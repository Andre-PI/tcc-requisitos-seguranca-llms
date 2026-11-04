import os
import hmac
import base64
import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH must be defined before import")

HASH_ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "200000"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "900"))
MAX_ATTEMPTS_PER_ACCOUNT = int(os.environ.get("MAX_ATTEMPTS_PER_ACCOUNT", "5"))
MAX_ATTEMPTS_PER_IP = int(os.environ.get("MAX_ATTEMPTS_PER_IP", "20"))

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app = FastAPI()

_lock = threading.Lock()


@dataclass
class RateLimitState:
    attempts: Deque[float]


_attempts_by_account: Dict[str, RateLimitState] = defaultdict(lambda: RateLimitState(deque()))
_attempts_by_ip: Dict[str, RateLimitState] = defaultdict(lambda: RateLimitState(deque()))


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: bytes | None = None, iterations: int = HASH_ITERATIONS) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(dk).decode("ascii"),
    )


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations_s, salt_b64, hash_b64 = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(hash_b64.encode("ascii"))
    except Exception:
        return False

    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(computed, expected)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _prune_and_count(state: RateLimitState, now: float) -> int:
    cutoff = now - LOGIN_WINDOW_SECONDS
    while state.attempts and state.attempts[0] < cutoff:
        state.attempts.popleft()
    return len(state.attempts)


def _is_rate_limited(account_key: str, ip_key: str) -> bool:
    now = time.time()
    with _lock:
        account_count = _prune_and_count(_attempts_by_account[account_key], now)
        ip_count = _prune_and_count(_attempts_by_ip[ip_key], now)
        return account_count >= MAX_ATTEMPTS_PER_ACCOUNT or ip_count >= MAX_ATTEMPTS_PER_IP


def _record_failed_attempt(account_key: str, ip_key: str) -> None:
    now = time.time()
    with _lock:
        _prune_and_count(_attempts_by_account[account_key], now)
        _prune_and_count(_attempts_by_ip[ip_key], now)
        _attempts_by_account[account_key].attempts.append(now)
        _attempts_by_ip[ip_key].attempts.append(now)


def _get_db() -> Session:
    return SessionLocal()


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn):
    email = _normalize_email(payload.email)
    hashed = _hash_password(payload.senha)
    with _get_db() as db:
        try:
            result = db.execute(
                text(
                    "INSERT INTO usuarios (email, senha, nome) "
                    "VALUES (:email, :senha, :nome)"
                ),
                {"email": email, "senha": hashed, "nome": payload.nome},
            )
            db.commit()
            user_id = result.lastrowid
            return {"id": int(user_id)}
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já existe")


@app.post("/login")
def login(payload: LoginIn, request: Request):
    email = _normalize_email(payload.email)
    ip = _client_ip(request)
    account_key = email
    ip_key = ip

    if _is_rate_limited(account_key, ip_key):
        _record_failed_attempt(account_key, ip_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    with _get_db() as db:
        row = db.execute(
            text("SELECT id, email, senha, nome FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": email},
        ).mappings().first()

    if not row or not _verify_password(payload.senha, row["senha"]):
        _record_failed_attempt(account_key, ip_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return {"id": int(row["id"]), "nome": row["nome"]}