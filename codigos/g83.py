from __future__ import annotations

import hmac
import hashlib
import logging
import os
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import String, Integer, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logger = logging.getLogger("auth")
logger.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# Database setup
# -----------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    poolclass=StaticPool if DATABASE_URL.startswith("sqlite") else None,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    senha: Mapped[str] = mapped_column(String(512), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)


Base.metadata.create_all(bind=engine)

# -----------------------------------------------------------------------------
# Password hashing
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class PasswordHashConfig:
    iterations: int = int(os.getenv("PASSWORD_HASH_ITERATIONS", "200000"))
    salt_bytes: int = int(os.getenv("PASSWORD_SALT_BYTES", "16"))
    dklen: int = int(os.getenv("PASSWORD_DKLEN", "32"))
    algorithm: str = "sha256"


PASSWORD_CONFIG = PasswordHashConfig()


def hash_password(password: str, *, iterations: int = PASSWORD_CONFIG.iterations) -> str:
    salt = secrets.token_bytes(PASSWORD_CONFIG.salt_bytes)
    dk = hashlib.pbkdf2_hmac(
        PASSWORD_CONFIG.algorithm,
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=PASSWORD_CONFIG.dklen,
    )
    return f"pbkdf2_{PASSWORD_CONFIG.algorithm}${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations_s, salt_hex, hash_hex = stored.split("$", 3)
        if not scheme.startswith("pbkdf2_"):
            return False
        algorithm = scheme.removeprefix("pbkdf2_")
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        candidate = hashlib.pbkdf2_hmac(
            algorithm,
            password.encode("utf-8"),
            salt,
            iterations,
            dklen=len(expected),
        )
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False


# -----------------------------------------------------------------------------
# Rate limiting
# -----------------------------------------------------------------------------
@dataclass
class AttemptWindow:
    max_attempts: int
    window_seconds: int
    attempts: Deque[float]

    def allow(self, now: float) -> bool:
        while self.attempts and now - self.attempts[0] > self.window_seconds:
            self.attempts.popleft()
        if len(self.attempts) >= self.max_attempts:
            return False
        self.attempts.append(now)
        return True


class LoginRateLimiter:
    def __init__(self, per_account_max: int = 5, per_ip_max: int = 20, window_seconds: int = 900):
        self.per_account_max = per_account_max
        self.per_ip_max = per_ip_max
        self.window_seconds = window_seconds
        self._by_account: Dict[str, AttemptWindow] = defaultdict(
            lambda: AttemptWindow(per_account_max, window_seconds, deque())
        )
        self._by_ip: Dict[str, AttemptWindow] = defaultdict(
            lambda: AttemptWindow(per_ip_max, window_seconds, deque())
        )

    def allow(self, account_key: str, ip_key: str) -> bool:
        now = time.monotonic()
        return self._by_account[account_key].allow(now) and self._by_ip[ip_key].allow(now)


rate_limiter = LoginRateLimiter()

# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


class LoginResponse(BaseModel):
    id: int
    nome: str


# -----------------------------------------------------------------------------
# FastAPI
# -----------------------------------------------------------------------------
app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = get_client_ip(request)
    account_key = payload.email.lower().strip()

    if not rate_limiter.allow(account_key, client_ip):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    user = db.execute(select(User).where(User.email == account_key)).scalar_one_or_none()

    # Dummy hash to reduce user enumeration via timing
    dummy_hash = hash_password("dummy-password")
    stored_hash = user.senha if user else dummy_hash

    if not verify_password(payload.senha, stored_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return LoginResponse(id=user.id, nome=user.nome)