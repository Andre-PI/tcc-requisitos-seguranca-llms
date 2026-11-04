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
from sqlalchemy.orm import sessionmaker, Session

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DB_URL = f"sqlite:///{DB_PATH}"

app = FastAPI()

engine = create_engine(DB_URL, future=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

HASH_ITERATIONS = int(os.environ.get("TCC_HASH_ITERATIONS", "210000"))
DUMMY_SALT = b"\x00" * 16
DUMMY_HASH = hashlib.pbkdf2_hmac("sha256", b"dummy-password", DUMMY_SALT, HASH_ITERATIONS)

MAX_ATTEMPTS_ACCOUNT = int(os.environ.get("TCC_MAX_LOGIN_ATTEMPTS_ACCOUNT", "5"))
MAX_ATTEMPTS_IP = int(os.environ.get("TCC_MAX_LOGIN_ATTEMPTS_IP", "20"))
WINDOW_SECONDS = int(os.environ.get("TCC_LOGIN_WINDOW_SECONDS", "900"))

_account_attempts: Dict[str, list[float]] = {}
_ip_attempts: Dict[str, list[float]] = {}


def _now() -> float:
    return time.time()


def _prune(attempts: list[float]) -> list[float]:
    cutoff = _now() - WINDOW_SECONDS
    return [ts for ts in attempts if ts >= cutoff]


def _rate_limited_account(email: str) -> bool:
    key = email.lower().strip()
    attempts = _account_attempts.get(key, [])
    attempts = _prune(attempts)
    _account_attempts[key] = attempts
    return len(attempts) >= MAX_ATTEMPTS_ACCOUNT


def _rate_limited_ip(ip: str) -> bool:
    attempts = _ip_attempts.get(ip, [])
    attempts = _prune(attempts)
    _ip_attempts[ip] = attempts
    return len(attempts) >= MAX_ATTEMPTS_IP


def _register_attempt(email: str, ip: str) -> None:
    key = email.lower().strip()
    _account_attempts.setdefault(key, []).append(_now())
    _ip_attempts.setdefault(ip, []).append(_now())


def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
    return f"pbkdf2_sha256${HASH_ITERATIONS}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iter_s, salt_hex, hash_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), DUMMY_SALT, HASH_ITERATIONS)
            return False
        iterations = int(iter_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(computed, expected)
    except Exception:
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), DUMMY_SALT, HASH_ITERATIONS)
        return False


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RegisterIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegisterIn, db: Session = Depends(get_db)):
    hashed = _hash_password(payload.senha)
    try:
        result = db.execute(
            text(
                "INSERT INTO usuarios (email, senha, nome) "
                "VALUES (:email, :senha, :nome)"
            ),
            {"email": str(payload.email).lower(), "senha": hashed, "nome": payload.nome},
        )
        db.commit()
        user_id = result.lastrowid
        return {"id": int(user_id)}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível registrar o usuário")


@app.post("/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    email_key = str(payload.email).lower().strip()

    if _rate_limited_account(email_key) or _rate_limited_ip(ip):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    row = db.execute(
        text("SELECT id, email, senha, nome FROM usuarios WHERE email = :email LIMIT 1"),
        {"email": email_key},
    ).mappings().first()

    if row is None:
        _register_attempt(email_key, ip)
        _verify_password(payload.senha, f"pbkdf2_sha256${HASH_ITERATIONS}${DUMMY_SALT.hex()}${DUMMY_HASH.hex()}")
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not _verify_password(payload.senha, row["senha"]):
        _register_attempt(email_key, ip)
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    return {"id": int(row["id"]), "nome": row["nome"]}