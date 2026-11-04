import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH", "usuarios.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

PBKDF2_ITERATIONS = int(os.environ.get("PBKDF2_ITERATIONS", "100000"))
DUMMY_SALT = secrets.token_hex(16)
DUMMY_HASH = hashlib.pbkdf2_hmac(
    "sha256", b"dummy_password", DUMMY_SALT.encode("utf-8"), PBKDF2_ITERATIONS
).hex()
DUMMY_PASSWORD_RECORD = f"pbkdf2_sha256${PBKDF2_ITERATIONS}${DUMMY_SALT}${DUMMY_HASH}"


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${pw_hash}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt, expected_hash = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        calculated_hash = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations
        ).hex()
        return hmac.compare_digest(calculated_hash, expected_hash)
    except Exception:
        return False


class RateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, List[float]] = defaultdict(list)
        self.lock = Lock()

    def is_limited(self, key: str) -> bool:
        now = time.time()
        with self.lock:
            timestamps = [t for t in self.attempts[key] if now - t < self.window_seconds]
            self.attempts[key] = timestamps
            return len(timestamps) >= self.max_attempts

    def record_attempt(self, key: str) -> None:
        now = time.time()
        with self.lock:
            timestamps = [t for t in self.attempts[key] if now - t < self.window_seconds]
            timestamps.append(now)
            self.attempts[key] = timestamps

    def reset(self, key: str) -> None:
        with self.lock:
            self.attempts.pop(key, None)


rate_limiter_ip = RateLimiter(max_attempts=5, window_seconds=300)
rate_limiter_email = RateLimiter(max_attempts=5, window_seconds=300)

app = FastAPI()


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class RegistroResponse(BaseModel):
    id: int


class LoginResponse(BaseModel):
    id: int
    nome: str


@app.post("/registro", status_code=status.HTTP_201_CREATED, response_model=RegistroResponse)
def registro(dados: RegistroRequest):
    with SessionLocal() as session:
        usuario_existente = session.scalar(select(Usuario).where(Usuario.email == dados.email))
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ja cadastrado",
            )

        hashed_senha = hash_password(dados.senha)
        novo_usuario = Usuario(email=dados.email, senha=hashed_senha, nome=dados.nome)
        session.add(novo_usuario)
        session.commit()
        session.refresh(novo_usuario)
        return {"id": novo_usuario.id}


@app.post("/login", response_model=LoginResponse)
def login(dados: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    ip_key = f"ip:{client_ip}"
    email_key = f"email:{dados.email}"

    if rate_limiter_ip.is_limited(ip_key) or rate_limiter_email.is_limited(email_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
        )

    with SessionLocal() as session:
        usuario = session.scalar(select(Usuario).where(Usuario.email == dados.email))

        if usuario:
            senha_valida = verify_password(dados.senha, usuario.senha)
        else:
            verify_password(dados.senha, DUMMY_PASSWORD_RECORD)
            senha_valida = False

        if not usuario or not senha_valida:
            rate_limiter_ip.record_attempt(ip_key)
            rate_limiter_email.record_attempt(email_key)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas",
            )

        rate_limiter_email.reset(email_key)
        return {"id": usuario.id, "nome": usuario.nome}