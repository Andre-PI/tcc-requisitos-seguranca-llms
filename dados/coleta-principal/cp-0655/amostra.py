import os
import time
import hmac
import hashlib
import secrets
from collections import defaultdict
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import declarative_base, sessionmaker

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

Base.metadata.create_all(bind=engine)

PBKDF2_ITERATIONS = 100_000

def hash_senha(senha: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}:{derived.hex()}"

def verificar_senha(senha_fornecida: str, senha_armazenada: str) -> bool:
    try:
        salt_hex, hash_hex = senha_armazenada.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        derived = hashlib.pbkdf2_hmac("sha256", senha_fornecida.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return hmac.compare_digest(derived, expected_hash)
    except Exception:
        return False

# Rate limiting em memória
# Janela de 5 minutos (300s), máximo de 5 tentativas por IP e por conta (e-mail)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300
attempts_by_ip: Dict[str, List[float]] = defaultdict(list)
attempts_by_email: Dict[str, List[float]] = defaultdict(list)

def check_rate_limit(key: str, store: Dict[str, List[float]]) -> bool:
    now = time.time()
    valid_attempts = [t for t in store[key] if now - t < WINDOW_SECONDS]
    store[key] = valid_attempts
    return len(valid_attempts) < MAX_ATTEMPTS

def record_attempt(key: str, store: Dict[str, List[float]]):
    store[key].append(time.time())

def clear_attempts(email: str):
    attempts_by_email.pop(email, None)

DUMMY_SALT = secrets.token_bytes(16).hex()
DUMMY_DERIVED = hashlib.pbkdf2_hmac("sha256", b"dummy_password", bytes.fromhex(DUMMY_SALT), PBKDF2_ITERATIONS).hex()
DUMMY_HASH = f"{DUMMY_SALT}:{DUMMY_DERIVED}"

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
    session = SessionLocal()
    try:
        usuario_existente = session.execute(
            select(Usuario).where(Usuario.email == dados.email)
        ).scalar_one_or_none()

        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ja cadastrado."
            )

        senha_hash = hash_senha(dados.senha)
        novo_usuario = Usuario(email=dados.email, senha=senha_hash, nome=dados.nome)
        session.add(novo_usuario)
        session.commit()
        session.refresh(novo_usuario)
        return {"id": novo_usuario.id}
    finally:
        session.close()

@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(dados: LoginRequest, request: Request):
    ip_origem = request.client.host if request.client else "unknown"
    email_key = dados.email.lower()

    if not check_rate_limit(ip_origem, attempts_by_ip) or not check_rate_limit(email_key, attempts_by_email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde."
        )

    session = SessionLocal()
    try:
        usuario = session.execute(
            select(Usuario).where(Usuario.email == dados.email)
        ).scalar_one_or_none()

        if usuario:
            hash_para_verificar = usuario.senha
        else:
            hash_para_verificar = DUMMY_HASH

        senha_valida = verificar_senha(dados.senha, hash_para_verificar)

        if not usuario or not senha_valida:
            record_attempt(ip_origem, attempts_by_ip)
            record_attempt(email_key, attempts_by_email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas."
            )

        clear_attempts(email_key)
        return {"id": usuario.id, "nome": usuario.nome}
    finally:
        session.close()