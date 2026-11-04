import os
import hmac
import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DB_URL = f"sqlite+pysqlite:///{DB_PATH}"
engine: Engine = create_engine(DB_URL, future=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

HASH_ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "210000"))
HASH_ALGO = "sha256"
SALT_BYTES = 16
DKLEN = 32

MAX_ATTEMPTS_PER_ACCOUNT = int(os.environ.get("LOGIN_MAX_ATTEMPTS_PER_ACCOUNT", "5"))
MAX_ATTEMPTS_PER_IP = int(os.environ.get("LOGIN_MAX_ATTEMPTS_PER_IP", "20"))
WINDOW_SECONDS = int(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))

_dummy_salt = secrets.token_bytes(SALT_BYTES)
_dummy_hash = hashlib.pbkdf2_hmac(HASH_ALGO, b"dummy-password", _dummy_salt, HASH_ITERATIONS, dklen=DKLEN)
_dummy_stored = f"pbkdf2_{HASH_ALGO}${HASH_ITERATIONS}${base64.b64encode(_dummy_salt).decode()}${base64.b64encode(_dummy_hash).decode()}"

_account_attempts: dict[str, list[float]] = {}
_ip_attempts: dict[str, list[float]] = {}


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _cleanup_attempts(store: dict[str, list[float]], key: str, now: float) -> list[float]:
    attempts = store.get(key, [])
    cutoff = now - WINDOW_SECONDS
    attempts = [ts for ts in attempts if ts >= cutoff]
    store[key] = attempts
    return attempts


def _allow_attempt(key: str, store: dict[str, list[float]], limit: int, now: float) -> bool:
    attempts = _cleanup_attempts(store, key, now)
    return len(attempts) < limit


def _record_attempt(key: str, store: dict[str, list[float]], now: float) -> None:
    attempts = _cleanup_attempts(store, key, now)
    attempts.append(now)
    store[key] = attempts


def _hash_password(password: str, salt: Optional[bytes] = None, iterations: Optional[int] = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(SALT_BYTES)
    if iterations is None:
        iterations = HASH_ITERATIONS
    dk = hashlib.pbkdf2_hmac(HASH_ALGO, password.encode("utf-8"), salt, iterations, dklen=DKLEN)
    return f"pbkdf2_{HASH_ALGO}${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iter_s, salt_b64, hash_b64 = stored.split("$", 3)
        if scheme != f"pbkdf2_{HASH_ALGO}":
            return False
        iterations = int(iter_s)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(hash_b64.encode())
        computed = hashlib.pbkdf2_hmac(HASH_ALGO, password.encode("utf-8"), salt, iterations, dklen=len(expected))
        return hmac.compare_digest(computed, expected)
    except Exception:
        _ = hmac.compare_digest(_dummy_hash, _dummy_hash)
        return False


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn, db: Session = Depends(get_db)):
    hashed = _hash_password(payload.senha)
    try:
        result = db.execute(
            text("INSERT INTO usuarios (email, senha, nome) VALUES (:email, :senha, :nome)"),
            {"email": payload.email, "senha": hashed, "nome": payload.nome},
        )
        db.commit()
        user_id = result.lastrowid
        return {"id": int(user_id)}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível registrar o usuário")


@app.post("/login")
def login(request: Request, payload: LoginIn, db: Session = Depends(get_db)):
    now = time.monotonic()
    client_ip = request.client.host if request.client else "unknown"
    email_key = payload.email.lower()

    if not _allow_attempt(email_key, _account_attempts, MAX_ATTEMPTS_PER_ACCOUNT, now) or not _allow_attempt(client_ip, _ip_attempts, MAX_ATTEMPTS_PER_IP, now):
        _record_attempt(email_key, _account_attempts, now)
        _record_attempt(client_ip, _ip_attempts, now)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    row = db.execute(
        text("SELECT id, nome, senha FROM usuarios WHERE email = :email LIMIT 1"),
        {"email": payload.email},
    ).mappings().first()

    if row is None:
        _ = _verify_password(payload.senha, _dummy_stored)
        _record_attempt(email_key, _account_attempts, now)
        _record_attempt(client_ip, _ip_attempts, now)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    if not _verify_password(payload.senha, row["senha"]):
        _record_attempt(email_key, _account_attempts, now)
        _record_attempt(client_ip, _ip_attempts, now)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    _account_attempts.pop(email_key, None)
    _ip_attempts.pop(client_ip, None)
    return {"id": int(row["id"]), "nome": row["nome"]}