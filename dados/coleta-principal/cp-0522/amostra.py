import os
import time
import secrets
import hashlib
import hmac
from collections import defaultdict
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Configuração do Banco de Dados
DB_PATH = os.environ.get("TCC_DB_PATH", "usuarios.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)


# Funções de Hash e Verificação usando PBKDF2 (padrão biblioteca padrão, seguro com custo configurável)
HASH_NAME = "sha256"
ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "100000"))
DUMMY_HASH = f"pbkdf2:{HASH_NAME}:{ITERATIONS}:{secrets.token_hex(16)}:{secrets.token_hex(32)}"


def hash_password(password: str, iterations: int = ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, iterations)
    return f"pbkdf2:{HASH_NAME}:{iterations}:{salt.hex()}:{key.hex()}"


def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    try:
        parts = stored_password_hash.split(":")
        if len(parts) != 5 or parts[0] != "pbkdf2":
            return False
        algorithm = parts[1]
        iterations = int(parts[2])
        salt = bytes.fromhex(parts[3])
        stored_key = bytes.fromhex(parts[4])
        computed_key = hashlib.pbkdf2_hmac(algorithm, provided_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(stored_key, computed_key)
    except Exception:
        return False


# Rate Limiter em memória para IP e Conta/E-mail
class RateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, List[float]] = defaultdict(list)

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        timestamps = self.attempts[key]
        self.attempts[key] = [t for t in timestamps if now - t < self.window_seconds]
        return len(self.attempts[key]) >= self.max_attempts

    def record_attempt(self, key: str):
        self.attempts[key].append(time.time())

    def reset(self, key: str):
        if key in self.attempts:
            del self.attempts[key]


ip_limiter = RateLimiter(max_attempts=10, window_seconds=300)
email_limiter = RateLimiter(max_attempts=5, window_seconds=300)

app = FastAPI()


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class RegistroResponse(BaseModel):
    id: int


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class LoginResponse(BaseModel):
    id: int
    nome: str


@app.post("/registro", status_code=status.HTTP_201_CREATED, response_model=RegistroResponse)
def registro(dados: RegistroRequest):
    with SessionLocal() as session:
        usuario_existente = session.execute(
            select(Usuario).where(Usuario.email == dados.email)
        ).scalar_one_or_none()
        if usuario_existente:
            raise HTTPException(status_code=400, detail="E-mail ja cadastrado")

        senha_hash = hash_password(dados.senha)
        novo_usuario = Usuario(email=dados.email, senha=senha_hash, nome=dados.nome)
        session.add(novo_usuario)
        session.commit()
        session.refresh(novo_usuario)
        return {"id": novo_usuario.id}


@app.post("/login", response_model=LoginResponse)
def login(dados: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    account_key = dados.email.lower()
    ip_key = client_ip

    if ip_limiter.is_rate_limited(ip_key) or email_limiter.is_rate_limited(account_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde."
        )

    with SessionLocal() as session:
        usuario = session.execute(
            select(Usuario).where(Usuario.email == dados.email)
        ).scalar_one_or_none()

        if usuario is not None:
            valido = verify_password(usuario.senha, dados.senha)
        else:
            verify_password(DUMMY_HASH, dados.senha)
            valido = False

    if not valido:
        ip_limiter.record_attempt(ip_key)
        email_limiter.record_attempt(account_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas"
        )

    email_limiter.reset(account_key)
    return {"id": usuario.id, "nome": usuario.nome}