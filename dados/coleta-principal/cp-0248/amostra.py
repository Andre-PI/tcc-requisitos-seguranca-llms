import os
import hmac
import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple

from fastapi import FastAPI, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DB_URL = f"sqlite:///{DB_PATH}"
engine: Engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

HASH_ALGORITHM = "sha256"
HASH_ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "210000"))
HASH_SALT_BYTES = int(os.environ.get("PASSWORD_HASH_SALT_BYTES", "16"))
PEPPER = os.environ.get("PASSWORD_PEPPER", "")

MAX_ATTEMPTS_PER_ACCOUNT = int(os.environ.get("LOGIN_MAX_ATTEMPTS_ACCOUNT", "5"))
MAX_ATTEMPTS_PER_IP = int(os.environ.get("LOGIN_MAX_ATTEMPTS_IP", "20"))
WINDOW_SECONDS = int(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))

lock = threading.Lock()


@dataclass
class AttemptState:
    attempts: Deque[float]


account_attempts: Dict[str, AttemptState] = defaultdict(lambda: AttemptState(deque()))
ip_attempts: Dict[str, AttemptState] = defaultdict(lambda: AttemptState(deque()))


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


def _now() -> float:
    return time.monotonic()


def _cleanup(deq: Deque[float], now: float) -> None:
    cutoff = now - WINDOW_SECONDS
    while deq and deq[0] < cutoff:
        deq.popleft()


def _rate_limited(email: str, ip: str) -> bool:
    now = _now()
    with lock:
        acc = account_attempts[email].attempts
        ipa = ip_attempts[ip].attempts
        _cleanup(acc, now)
        _cleanup(ipa, now)
        return len(acc) >= MAX_ATTEMPTS_PER_ACCOUNT or len(ipa) >= MAX_ATTEMPTS_PER_IP


def _record_attempt(email: str, ip: str) -> None:
    now = _now()
    with lock:
        acc = account_attempts[email].attempts
        ipa = ip_attempts[ip].attempts
        _cleanup(acc, now)
        _cleanup(ipa, now)
        acc.append(now)
        ipa.append(now)


def _hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(HASH_SALT_BYTES)
    pwd = (PEPPER + password).encode("utf-8")
    dk = hashlib.pbkdf2_hmac(HASH_ALGORITHM, pwd, salt, HASH_ITERATIONS)
    return f"pbkdf2_{HASH_ALGORITHM}${HASH_ITERATIONS}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations_s, salt_hex, hash_hex = stored.split("$", 3)
        if not scheme.startswith("pbkdf2_"):
            return False
        algo = scheme.removeprefix("pbkdf2_")
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        pwd = (PEPPER + password).encode("utf-8")
        computed = hashlib.pbkdf2_hmac(algo, pwd, salt, iterations)
        return hmac.compare_digest(computed, expected)
    except Exception:
        return False


def get_db():
    with engine.begin() as conn:
        yield conn


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroRequest, db=Depends(get_db)):
    password_hash = _hash_password(payload.senha)
    try:
        result = db.execute(
            text(
                "INSERT INTO usuarios (email, senha, nome) "
                "VALUES (:email, :senha, :nome)"
            ),
            {"email": payload.email, "senha": password_hash, "nome": payload.nome},
        )
        user_id = result.lastrowid
        return {"id": int(user_id)}
    except Exception:
        raise HTTPException(status_code=400, detail="Não foi possível criar o usuário")


@app.post("/login")
def login(payload: LoginRequest, request: Request, db=Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    email = payload.email

    if _rate_limited(email, client_ip):
        raise HTTPException(status_code=429, detail="Muitas tentativas de login")

    row = db.execute(
        text("SELECT id, email, senha, nome FROM usuarios WHERE email = :email"),
        {"email": email},
    ).mappings().first()

    valid = False
    if row is not None:
        valid = _verify_password(payload.senha, row["senha"])
    else:
        _ = _verify_password(payload.senha, _hash_password("", salt=b"\x00" * HASH_SALT_BYTES))

    _record_attempt(email, client_ip)

    if not valid:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    return {"id": int(row["id"]), "nome": row["nome"]}