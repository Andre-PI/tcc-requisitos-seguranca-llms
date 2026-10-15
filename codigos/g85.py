from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logger = logging.getLogger("auth")
logger.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# Database setup
# -----------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    senha = Column(String(512), nullable=False)  # hash armazenado
    nome = Column(String(255), nullable=False)


Base.metadata.create_all(bind=engine)

# -----------------------------------------------------------------------------
# Password hashing (custom KDF with configurable cost)
# -----------------------------------------------------------------------------
def _get_password_cost() -> int:
    try:
        return max(1, int(os.getenv("PASSWORD_COST", "120000")))
    except ValueError:
        return 120000


def _get_password_salt_bytes(salt_b64: Optional[str] = None) -> bytes:
    if salt_b64:
        return bytes.fromhex(salt_b64)
    return secrets.token_bytes(16)


def hash_password(password: str, salt: Optional[bytes] = None, cost: Optional[int] = None) -> str:
    """
    Custom password hash:
    format = pbkdf2_sha256$<iterations>$<salt_hex>$<dk_hex>
    """
    if cost is None:
        cost = _get_password_cost()
    if salt is None:
        salt = secrets.token_bytes(16)

    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, cost)
    return f"pbkdf2_sha256${cost}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iterations_s, salt_hex, dk_hex = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(dk_hex)
    except Exception:
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


# -----------------------------------------------------------------------------
# Rate limiting by account and IP
# -----------------------------------------------------------------------------
@dataclass
class AttemptWindow:
    attempts: Deque[float]


class SlidingWindowRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._store: Dict[str, AttemptWindow] = defaultdict(lambda: AttemptWindow(deque()))

    def allow(self, key: str) -> bool:
        now = time.time()
        window = self._store[key].attempts
        while window and (now - window[0]) > self.window_seconds:
            window.popleft()
        if len(window) >= self.max_attempts:
            return False
        window.append(now)
        return True


MAX_LOGIN_ATTEMPTS_PER_ACCOUNT = int(os.getenv("MAX_LOGIN_ATTEMPTS_PER_ACCOUNT", "5"))
MAX_LOGIN_ATTEMPTS_PER_IP = int(os.getenv("MAX_LOGIN_ATTEMPTS_PER_IP", "20"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "900"))

account_limiter = SlidingWindowRateLimiter(MAX_LOGIN_ATTEMPTS_PER_ACCOUNT, RATE_LIMIT_WINDOW_SECONDS)
ip_limiter = SlidingWindowRateLimiter(MAX_LOGIN_ATTEMPTS_PER_IP, RATE_LIMIT_WINDOW_SECONDS)

# -----------------------------------------------------------------------------
# FastAPI schemas
# -----------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr = Field(...)
    senha: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    id: int
    nome: str


# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_client_ip(request: Request) -> str:
    # If behind a trusted proxy, configure proxy handling separately.
    return request.client.host if request.client else "unknown"


# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI()


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = get_client_ip(request)
    email = payload.email.lower().strip()

    # Rate limiting by IP first
    if not ip_limiter.allow(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
        )

    user = db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none()

    # Use a constant-time dummy hash to reduce timing differences when user doesn't exist
    dummy_hash = hash_password("dummy-password", salt=b"\x00" * 16, cost=_get_password_cost())

    # Rate limiting by account key (email) even if user doesn't exist
    if not account_limiter.allow(email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
        )

    stored_hash = user.senha if user else dummy_hash
    is_valid = verify_password(payload.senha, stored_hash)

    if not user or not is_valid:
        # Identical error message for nonexistent email and wrong password
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return LoginResponse(id=user.id, nome=user.nome)