import os
import time
import secrets
import hashlib
import hmac
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, select, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH", "database.db")
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

PBKDF2_ITERATIONS = 100_000

def hash_senha(senha: str, salt: bytes | None = None, iterations: int = PBKDF2_ITERATIONS) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iterations)
    return f"{iterations}${salt.hex()}${dk.hex()}"

def verificar_senha(senha_fornecida: str, hash_armazenado: str) -> bool:
    try:
        parts = hash_armazenado.split("$")
        if len(parts) != 3:
            return False
        iterations_str, salt_hex, hash_hex = parts
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", senha_fornecida.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected_hash)
    except Exception:
        return False

# Rate limiting in-memory
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_ATTEMPTS = 5

ip_attempts = defaultdict(list)
account_attempts = defaultdict(list)

def is_rate_limited(ip: str, email: str) -> bool:
    now = time.time()
    
    ip_attempts[ip] = [t for t in ip_attempts[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(ip_attempts[ip]) >= RATE_LIMIT_MAX_ATTEMPTS:
        return True

    account_attempts[email] = [t for t in account_attempts[email] if now - t < RATE_LIMIT_WINDOW]
    if len(account_attempts[email]) >= RATE_LIMIT_MAX_ATTEMPTS:
        return True

    return False

def record_attempt(ip: str, email: str):
    now = time.time()
    ip_attempts[ip].append(now)
    account_attempts[email].append(now)

def get_client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

DUMMY_SALT = secrets.token_bytes(16)
DUMMY_HASH = hash_senha("dummy_password_for_timing_safety", salt=DUMMY_SALT, iterations=PBKDF2_ITERATIONS)

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

@app.post("/registro", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def registro(dados: RegistroRequest):
    email_normalizado = dados.email.lower()
    with SessionLocal() as db:
        usuario_existente = db.execute(
            select(Usuario).filter(Usuario.email == email_normalizado)
        ).scalar_one_or_none()

        if usuario_existente:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ja cadastrado")

        senha_hasheada = hash_senha(dados.senha)
        novo_usuario = Usuario(
            email=email_normalizado,
            senha=senha_hasheada,
            nome=dados.nome
        )
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)

        return {"id": novo_usuario.id}

@app.post("/login", response_model=LoginResponse)
def login(dados: LoginRequest, request: Request):
    ip = get_client_ip(request)
    email_normalizado = dados.email.lower()

    if is_rate_limited(ip, email_normalizado):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde."
        )

    with SessionLocal() as db:
        usuario = db.execute(
            select(Usuario).filter(Usuario.email == email_normalizado)
        ).scalar_one_or_none()

        if usuario is None:
            verificar_senha(dados.senha, DUMMY_HASH)
            record_attempt(ip, email_normalizado)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas"
            )

        if not verificar_senha(dados.senha, usuario.senha):
            record_attempt(ip, email_normalizado)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas"
            )

        return {"id": usuario.id, "nome": usuario.nome}