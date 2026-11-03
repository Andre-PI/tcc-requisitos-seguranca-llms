import os
import hmac
import base64
import hashlib
import secrets
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite+pysqlite:///{DB_PATH}"
engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

PBKDF2_ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "200000"))
PASSWORD_SALT_BYTES = int(os.environ.get("PASSWORD_SALT_BYTES", "16"))
MAX_ATTEMPTS_PER_ACCOUNT = int(os.environ.get("LOGIN_MAX_ATTEMPTS_ACCOUNT", "5"))
MAX_ATTEMPTS_PER_IP = int(os.environ.get("LOGIN_MAX_ATTEMPTS_IP", "20"))
ATTEMPT_WINDOW_SECONDS = int(os.environ.get("LOGIN_ATTEMPT_WINDOW_SECONDS", "900"))

_account_attempts: dict[str, deque[float]] = defaultdict(deque)
_ip_attempts: dict[str, deque[float]] = defaultdict(deque)

_dummy_salt = b"0" * PASSWORD_SALT_BYTES
_dummy_hash = hashlib.pbkdf2_hmac("sha256", b"dummy-password", _dummy_salt, PBKDF2_ITERATIONS)

class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)

class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)

def _now() -> float:
    return time.monotonic()

def _cleanup_attempts(bucket: deque[float], now: float) -> None:
    cutoff = now - ATTEMPT_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()

def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"

def _rate_limited(key: str, store: dict[str, deque[float]], limit: int, now: float) -> bool:
    bucket = store[key]
    _cleanup_attempts(bucket, now)
    return len(bucket) >= limit

def _record_attempt(key: str, store: dict[str, deque[float]], now: float) -> None:
    bucket = store[key]
    _cleanup_attempts(bucket, now)
    bucket.append(now)

def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(dk).decode("ascii"),
    )

def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iter_s, salt_b64, hash_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_s)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(hash_b64.encode("ascii"))
    except Exception:
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _dummy_salt, PBKDF2_ITERATIONS)
        return False

    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(computed, expected)

@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn):
    db = SessionLocal()
    try:
        hashed = _hash_password(payload.senha)
        result = db.execute(
            text(
                "INSERT INTO usuarios (email, senha, nome) "
                "VALUES (:email, :senha, :nome)"
            ),
            {"email": payload.email, "senha": hashed, "nome": payload.nome},
        )
        db.commit()
        user_id = result.lastrowid
        return {"id": int(user_id)}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Usuário já existe")
    finally:
        db.close()

@app.post("/login")
def login(payload: LoginIn, request: Request):
    now = _now()
    ip = _client_ip(request)
    email = payload.email.lower()

    if _rate_limited(email, _account_attempts, MAX_ATTEMPTS_PER_ACCOUNT, now) or _rate_limited(ip, _ip_attempts, MAX_ATTEMPTS_PER_IP, now):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT id, email, senha, nome FROM usuarios WHERE email = :email"),
            {"email": payload.email},
        ).mappings().first()

        if row is None:
            _verify_password(payload.senha, "pbkdf2_sha256$1$ZmFrZXNhbHQ=$ZmFrZWhhc2g=")
            _record_attempt(email, _account_attempts, now)
            _record_attempt(ip, _ip_attempts, now)
            raise HTTPException(status_code=401, detail="Credenciais inválidas")

        if not _verify_password(payload.senha, row["senha"]):
            _record_attempt(email, _account_attempts, now)
            _record_attempt(ip, _ip_attempts, now)
            raise HTTPException(status_code=401, detail="Credenciais inválidas")

        return {"id": int(row["id"]), "nome": row["nome"]}
    finally:
        db.close()