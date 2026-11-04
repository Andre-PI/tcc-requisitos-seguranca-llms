import os
import hmac
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

from fastapi import FastAPI, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session

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
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

HASH_ALGORITHM = "sha256"
HASH_ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "200000"))
SALT_BYTES = int(os.environ.get("PASSWORD_SALT_BYTES", "16"))
DUMMY_SALT = b"\x00" * SALT_BYTES
DUMMY_HASH = hashlib.pbkdf2_hmac(HASH_ALGORITHM, b"dummy-password", DUMMY_SALT, HASH_ITERATIONS).hex()

MAX_ATTEMPTS_PER_ACCOUNT = int(os.environ.get("LOGIN_MAX_ATTEMPTS_ACCOUNT", "5"))
MAX_ATTEMPTS_PER_IP = int(os.environ.get("LOGIN_MAX_ATTEMPTS_IP", "20"))
WINDOW_SECONDS = int(os.environ.get("LOGIN_RATE_WINDOW_SECONDS", "900"))

account_attempts: Dict[str, list[float]] = {}
ip_attempts: Dict[str, list[float]] = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: bytes, iterations: int = HASH_ITERATIONS) -> str:
    dk = hashlib.pbkdf2_hmac(HASH_ALGORITHM, password.encode("utf-8"), salt, iterations)
    return f"{iterations}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        iterations_s, salt_hex, hash_hex = stored.split("$", 2)
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        _ = hashlib.pbkdf2_hmac(HASH_ALGORITHM, password.encode("utf-8"), DUMMY_SALT, HASH_ITERATIONS)
        return False

    computed = hashlib.pbkdf2_hmac(HASH_ALGORITHM, password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(computed, expected)


def _cleanup_attempts(store: Dict[str, list[float]], key: str, now: float) -> None:
    attempts = store.get(key)
    if not attempts:
        return
    cutoff = now - WINDOW_SECONDS
    store[key] = [t for t in attempts if t >= cutoff]
    if not store[key]:
        store.pop(key, None)


def _record_attempt(store: Dict[str, list[float]], key: str, now: float) -> None:
    store.setdefault(key, []).append(now)
    _cleanup_attempts(store, key, now)


def _too_many_attempts(account_key: str, ip_key: str, now: float) -> bool:
    _cleanup_attempts(account_attempts, account_key, now)
    _cleanup_attempts(ip_attempts, ip_key, now)
    return (
        len(account_attempts.get(account_key, [])) >= MAX_ATTEMPTS_PER_ACCOUNT
        or len(ip_attempts.get(ip_key, [])) >= MAX_ATTEMPTS_PER_IP
    )


def _generic_login_error() -> None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    salt = secrets.token_bytes(SALT_BYTES)
    senha_hash = _hash_password(payload.senha, salt)

    try:
        result = db.execute(
            text("INSERT INTO usuarios (email, senha, nome) VALUES (:email, :senha, :nome)"),
            {"email": email, "senha": senha_hash, "nome": payload.nome},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já cadastrado")

    user_id = result.lastrowid
    return {"id": int(user_id)}


@app.post("/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()

    if _too_many_attempts(email, client_ip, now):
        _generic_login_error()

    row = db.execute(
        text("SELECT id, email, senha, nome FROM usuarios WHERE email = :email"),
        {"email": email},
    ).mappings().first()

    stored_password = row["senha"] if row else DUMMY_HASH
    ok = _verify_password(payload.senha, stored_password)

    _record_attempt(account_attempts, email, now)
    _record_attempt(ip_attempts, client_ip, now)

    if not row or not ok:
        _generic_login_error()

    return {"id": int(row["id"]), "nome": row["nome"]}