from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import hmac
import hashlib
import secrets
import os
import time
import threading
import logging
from collections import defaultdict, deque

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "210000"))
PBKDF2_SALT_BYTES = int(os.getenv("PBKDF2_SALT_BYTES", "16"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "300"))
MAX_ATTEMPTS_PER_ACCOUNT = int(os.getenv("MAX_ATTEMPTS_PER_ACCOUNT", "5"))
MAX_ATTEMPTS_PER_IP = int(os.getenv("MAX_ATTEMPTS_PER_IP", "20"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth")
logger.propagate = False

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    senha = Column(String(255), nullable=False)
    nome = Column(String(255), nullable=False)

Base.metadata.create_all(bind=engine)

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)

class LoginResponse(BaseModel):
    id: int
    nome: str

app = FastAPI()
security = HTTPBearer(auto_error=False)

class RateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self._account_attempts = defaultdict(deque)
        self._ip_attempts = defaultdict(deque)

    def _prune(self, dq):
        cutoff = time.time() - RATE_LIMIT_WINDOW_SECONDS
        while dq and dq[0] < cutoff:
            dq.popleft()

    def allow(self, account_key: str, ip_key: str) -> bool:
        now = time.time()
        with self._lock:
            acc = self._account_attempts[account_key]
            ip = self._ip_attempts[ip_key]
            self._prune(acc)
            self._prune(ip)
            if len(acc) >= MAX_ATTEMPTS_PER_ACCOUNT or len(ip) >= MAX_ATTEMPTS_PER_IP:
                return False
            acc.append(now)
            ip.append(now)
            return True

rate_limiter = RateLimiter()

def hash_password(password: str, salt: bytes | None = None, iterations: int = PBKDF2_ITERATIONS) -> str:
    if salt is None:
        salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iterations_s, salt_hex, hash_hex = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(computed, expected)
    except Exception:
        dummy_salt = b"\x00" * PBKDF2_SALT_BYTES
        dummy_expected = b"\x00" * 32
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), dummy_salt, PBKDF2_ITERATIONS)
        hmac.compare_digest(computed, dummy_expected)
        return False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    account_key = payload.email.lower().strip()

    if not rate_limiter.allow(account_key, ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Muitas tentativas de login. Tente novamente mais tarde.")

    try:
        user = db.execute(select(Usuario).where(Usuario.email == account_key)).scalar_one_or_none()
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno.")

    password_ok = False
    if user is not None:
        password_ok = verify_password(payload.senha, user.senha)
    else:
        verify_password(payload.senha, "pbkdf2_sha256$210000$00000000000000000000000000000000$0000000000000000000000000000000000000000000000000000000000000000")

    if not user or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")

    return LoginResponse(id=user.id, nome=user.nome)