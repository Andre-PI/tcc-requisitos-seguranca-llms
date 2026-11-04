import os
import hmac
import time
import base64
import hashlib
import secrets
import threading
from dataclasses import dataclass
from typing import Optional

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

HASH_ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "210000"))
HASH_ALGORITHM = "sha256"
SALT_BYTES = 16
DKLEN = 32
MAX_ATTEMPTS_PER_EMAIL = int(os.environ.get("LOGIN_MAX_ATTEMPTS_PER_EMAIL", "5"))
MAX_ATTEMPTS_PER_IP = int(os.environ.get("LOGIN_MAX_ATTEMPTS_PER_IP", "20"))
WINDOW_SECONDS = int(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


class LoginSuccess(BaseModel):
    id: int
    nome: str


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _pbkdf2_hash(password: str, salt: bytes, iterations: int = HASH_ITERATIONS) -> bytes:
    return hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=DKLEN,
    )


def hash_password(password: str, iterations: int = HASH_ITERATIONS) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    dk = _pbkdf2_hash(password, salt, iterations)
    return f"pbkdf2_{HASH_ALGORITHM}${iterations}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(dk).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iter_s, salt_b64, dk_b64 = stored_hash.split("$", 3)
        if not algo.startswith("pbkdf2_"):
            return False
        iterations = int(iter_s)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(dk_b64.encode())
    except Exception:
        return False

    computed = _pbkdf2_hash(password, salt, iterations)
    return hmac.compare_digest(computed, expected)


@dataclass
class _Counter:
    count: int
    reset_at: float


class RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_email: dict[str, _Counter] = {}
        self._by_ip: dict[str, _Counter] = {}

    def _cleanup(self, store: dict[str, _Counter], now: float) -> None:
        expired = [k for k, v in store.items() if v.reset_at <= now]
        for k in expired:
            del store[k]

    def _increment(self, store: dict[str, _Counter], key: str, limit: int, now: float) -> bool:
        self._cleanup(store, now)
        c = store.get(key)
        if c is None:
            store[key] = _Counter(count=1, reset_at=now + WINDOW_SECONDS)
            return True
        if c.count >= limit:
            return False
        c.count += 1
        return True

    def allow(self, email: str, ip: str) -> bool:
        now = time.time()
        email_key = email.lower()
        ip_key = ip or "unknown"
        with self._lock:
            if not self._increment(self._by_email, email_key, MAX_ATTEMPTS_PER_EMAIL, now):
                return False
            if not self._increment(self._by_ip, ip_key, MAX_ATTEMPTS_PER_IP, now):
                return False
            return True

    def reset_email(self, email: str) -> None:
        with self._lock:
            self._by_email.pop(email.lower(), None)


rate_limiter = RateLimiter()


def _get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _generic_login_failure() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn, db: Session = Depends(get_db)):
    senha_hash = hash_password(payload.senha)
    try:
        result = db.execute(
            text(
                "INSERT INTO usuarios (email, senha, nome) "
                "VALUES (:email, :senha, :nome)"
            ),
            {"email": payload.email.lower(), "senha": senha_hash, "nome": payload.nome},
        )
        db.commit()
        user_id = result.lastrowid
        return {"id": int(user_id)}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Usuário já existe")


@app.post("/login", response_model=LoginSuccess)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    client_ip = _get_client_ip(request)
    if not rate_limiter.allow(payload.email, client_ip):
        raise HTTPException(status_code=429, detail="Muitas tentativas de login")

    row = db.execute(
        text("SELECT id, email, senha, nome FROM usuarios WHERE email = :email LIMIT 1"),
        {"email": payload.email.lower()},
    ).mappings().first()

    if row is None:
        verify_password(payload.senha, hash_password("dummy_password"))
        raise _generic_login_failure()

    if not verify_password(payload.senha, row["senha"]):
        raise _generic_login_failure()

    rate_limiter.reset_email(payload.email)
    return {"id": int(row["id"]), "nome": row["nome"]}