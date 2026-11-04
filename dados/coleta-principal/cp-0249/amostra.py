import os
import hmac
import time
import secrets
from collections import defaultdict
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import declarative_base, sessionmaker

# Algoritmo de hash de senha padrão: PBKDF2-HMAC-SHA256
PBKDF2_ITERATIONS = int(os.environ.get("PBKDF2_ITERATIONS", "100000"))
SALT_BYTES = 16

# Rate Limiting: máximo de 5 tentativas por janela de 300 segundos (por IP e por conta)
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 300

ip_attempts: Dict[str, List[float]] = defaultdict(list)
account_attempts: Dict[str, List[float]] = defaultdict(list)

# Banco de dados
db_path = os.environ.get("TCC_DB_PATH", "usuarios.db")
engine = create_engine(
    f"sqlite:///{db_path}",
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

def hash_senha(senha: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    derived = hmac.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"

def verificar_senha(senha: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_hex, derived_hex = stored_hash.replace(":", "$").split("$")
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(derived_hex)
    except Exception:
        return False

    derived = hmac.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(derived, expected)

DUMMY_HASH = hash_senha("dummy_timing_protection_secret")

def is_rate_limited(key: str, storage: Dict[str, List[float]]) -> bool:
    now = time.time()
    valid_attempts = [t for t in storage[key] if now - t < RATE_LIMIT_WINDOW]
    storage[key] = valid_attempts
    return len(valid_attempts) >= RATE_LIMIT_MAX_ATTEMPTS

def register_attempt(key: str, storage: Dict[str, List[float]]) -> None:
    storage[key].append(time.time())

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
            select(Usuario).where(Usuario.email == email_normalizado)
        ).scalar_one_or_none()
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ja cadastrado."
            )

        novo_usuario = Usuario(
            email=email_normalizado,
            senha=hash_senha(dados.senha),
            nome=dados.nome
        )
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        return RegistroResponse(id=novo_usuario.id)

@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(dados: LoginRequest, request: Request):
    ip_origem = request.client.host if request.client else "unknown"
    email_normalizado = dados.email.lower()

    if is_rate_limited(ip_origem, ip_attempts) or is_rate_limited(email_normalizado, account_attempts):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde."
        )

    with SessionLocal() as db:
        usuario = db.execute(
            select(Usuario).where(Usuario.email == email_normalizado)
        ).scalar_one_or_none()

        if usuario:
            senha_valida = verificar_senha(dados.senha, usuario.senha)
        else:
            verificar_senha(dados.senha, DUMMY_HASH)
            senha_valida = False

        if not senha_valida:
            register_attempt(ip_origem, ip_attempts)
            register_attempt(email_normalizado, account_attempts)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas."
            )

        ip_attempts[ip_origem] = []
        account_attempts[email_normalizado] = []

        return LoginResponse(id=usuario.id, nome=usuario.nome)