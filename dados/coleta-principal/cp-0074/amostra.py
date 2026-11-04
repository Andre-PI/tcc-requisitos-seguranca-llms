import os
import hmac
import hashlib
import secrets
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DB_PATH = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not DB_PATH.startswith("sqlite:///"):
    DB_URL = f"sqlite:///{DB_PATH}"
else:
    DB_URL = DB_PATH

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
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
    key = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}:{PBKDF2_ITERATIONS}:{key.hex()}"

def verificar_senha(senha: str, stored_hash: str) -> bool:
    try:
        salt_hex, iter_str, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        iterations = int(iter_str)
        target_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(key, target_key)
    except Exception:
        return False

DUMMY_SALT = secrets.token_bytes(16)
DUMMY_KEY = hashlib.pbkdf2_hmac("sha256", b"dummy_password", DUMMY_SALT, PBKDF2_ITERATIONS)
DUMMY_HASH = f"{DUMMY_SALT.hex()}:{PBKDF2_ITERATIONS}:{DUMMY_KEY.hex()}"

RATE_LIMIT_WINDOW = 300
MAX_ATTEMPTS = 5

ip_attempts: Dict[str, List[float]] = defaultdict(list)
email_attempts: Dict[str, List[float]] = defaultdict(list)

def check_rate_limit(key: str, store: Dict[str, List[float]]) -> bool:
    now = time.time()
    store[key] = [t for t in store[key] if now - t < RATE_LIMIT_WINDOW]
    return len(store[key]) >= MAX_ATTEMPTS

def record_attempt(key: str, store: Dict[str, List[float]]):
    now = time.time()
    store[key].append(now)

def reset_rate_limit(key: str, store: Dict[str, List[float]]):
    if key in store:
        del store[key]

app = FastAPI()

class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroRequest):
    email_clean = payload.email.strip().lower()
    hashed = hash_senha(payload.senha)
    with SessionLocal() as db:
        user = db.execute(select(Usuario).filter(Usuario.email == email_clean)).scalar_one_or_none()
        if user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario ja cadastrado")
        novo_usuario = Usuario(
            email=email_clean,
            senha=hashed,
            nome=payload.nome.strip()
        )
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        return {"id": novo_usuario.id}

@app.post("/login", status_code=status.HTTP_200_OK)
def login(payload: LoginRequest, request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    email_clean = payload.email.strip().lower()

    if check_rate_limit(ip, ip_attempts) or check_rate_limit(email_clean, email_attempts):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde."
        )

    with SessionLocal() as db:
        user = db.execute(select(Usuario).filter(Usuario.email == email_clean)).scalar_one_or_none()

    if user is not None:
        valido = verificar_senha(payload.senha, user.senha)
    else:
        verificar_senha(payload.senha, DUMMY_HASH)
        valido = False

    if not valido:
        record_attempt(ip, ip_attempts)
        record_attempt(email_clean, email_attempts)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas"
        )

    reset_rate_limit(email_clean, email_attempts)
    return {"id": user.id, "nome": user.nome}