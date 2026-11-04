import os
import hmac
import base64
import hashlib
import secrets
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Deque, Dict, Tuple

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

HASH_ITERATIONS = int(os.environ.get("TCC_PBKDF2_ITERATIONS", "210000"))
HASH_ALGORITHM = os.environ.get("TCC_PBKDF2_ALGORITHM", "sha256")
HASH_SALT_BYTES = int(os.environ.get("TCC_PBKDF2_SALT_BYTES", "16"))

LOGIN_MAX_ATTEMPTS_PER_ACCOUNT = int(os.environ.get("TCC_LOGIN_MAX_ATTEMPTS_PER_ACCOUNT", "5"))
LOGIN_MAX_ATTEMPTS_PER_IP = int(os.environ.get("TCC_LOGIN_MAX_ATTEMPTS_PER_IP", "20"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("TCC_LOGIN_WINDOW_SECONDS", "900"))

engine: Engine = create_engine(
    f"sqlite:///{DB_PATH}",
    future=True,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
)

_fake_salt = secrets.token_bytes(HASH_SALT_BYTES)
_fake_hash = hashlib.pbkdf2_hmac(HASH_ALGORITHM, b"constant", _fake_salt, HASH_ITERATIONS)

_account_attempts: Dict[str, Deque[float]] = defaultdict(deque)
_ip_attempts: Dict[str, Deque[float]] = defaultdict(deque)


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


def _now() -> float:
    return time.monotonic()


def _prune(attempts: Deque[float], now: float) -> None:
    cutoff = now - LOGIN_WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()


def _rate_limited(email: str, ip: str) -> bool:
    now = _now()
    acc = _account_attempts[email]
    ipq = _ip_attempts[ip]
    _prune(acc, now)
    _prune(ipq, now)
    return len(acc) >= LOGIN_MAX_ATTEMPTS_PER_ACCOUNT or len(ipq) >= LOGIN_MAX_ATTEMPTS_PER_IP


def _record_attempt(email: str, ip: str) -> None:
    now = _now()
    acc = _account_attempts[email]
    ipq = _ip_attempts[ip]
    _prune(acc, now)
    _prune(ipq, now)
    acc.append(now)
    ipq.append(now)


def _normalize_password(password: str) -> bytes:
    return password.encode("utf-8")


def hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(HASH_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(HASH_ALGORITHM, _normalize_password(password), salt, HASH_ITERATIONS)
    return f"pbkdf2_{HASH_ALGORITHM}${HASH_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo_tag, iterations_s, salt_b64, hash_b64 = stored_hash.split("$", 3)
        if not algo_tag.startswith("pbkdf2_"):
            raise ValueError
        algo = algo_tag.removeprefix("pbkdf2_")
        iterations = int(iterations_s)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(hash_b64.encode())
    except Exception:
        salt = _fake_salt
        iterations = HASH_ITERATIONS
        algo = HASH_ALGORITHM
        expected = _fake_hash

    candidate = hashlib.pbkdf2_hmac(algo, _normalize_password(password), salt, iterations)
    return hmac.compare_digest(candidate, expected)


@contextmanager
def get_conn():
    with engine.begin() as conn:
        yield conn


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn):
    hashed = hash_password(payload.senha)
    try:
        with get_conn() as conn:
            result = conn.execute(
                text(
                    "INSERT INTO usuarios (email, senha, nome) "
                    "VALUES (:email, :senha, :nome)"
                ),
                {"email": payload.email, "senha": hashed, "nome": payload.nome},
            )
            user_id = result.lastrowid
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já existe")
    return {"id": int(user_id)}


@app.post("/login")
def login(payload: LoginIn, request: Request):
    ip = _client_ip(request)
    email = payload.email

    if _rate_limited(email, ip):
        _record_attempt(email, ip)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Muitas tentativas de login")

    with get_conn() as conn:
        row = conn.execute(
            text("SELECT id, email, senha, nome FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": email},
        ).mappings().first()

    valid = False
    user_id = None
    nome = None

    if row is not None:
        valid = verify_password(payload.senha, row["senha"])
        if valid:
            user_id = row["id"]
            nome = row["nome"]
    else:
        verify_password(payload.senha, f"pbkdf2_{HASH_ALGORITHM}${HASH_ITERATIONS}${base64.b64encode(_fake_salt).decode()}${base64.b64encode(_fake_hash).decode()}")

    _record_attempt(email, ip)

    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return {"id": int(user_id), "nome": nome}