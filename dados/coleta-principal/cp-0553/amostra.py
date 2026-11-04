import os
import time
import hmac
import hashlib
import secrets
from collections import defaultdict
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, select, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Configuração de hash de senhas (PBKDF2-HMAC-SHA256)
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16

# Dummy hash para mitigar timing attacks na ausência de usuário
DUMMY_SALT = secrets.token_hex(SALT_BYTES)
DUMMY_HASH = hashlib.pbkdf2_hmac(
    "sha256", b"dummy_password", bytes.fromhex(DUMMY_SALT), PBKDF2_ITERATIONS
).hex()
DUMMY_PASSWORD_STORED = f"{DUMMY_SALT}${DUMMY_HASH}"

def hash_senha(senha: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    ).hex()
    return f"{salt}${derived}"

def verificar_senha(senha: str, senha_armazenada: str) -> bool:
    try:
        salt_hex, expected_hash = senha_armazenada.split("$")
        derived = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), bytes.fromhex(salt_hex), PBKDF2_ITERATIONS
        ).hex()
        return hmac.compare_digest(derived, expected_hash)
    except Exception:
        return False

# Rate Limiter em memória por IP e Email
# Janela de 15 minutos (900s), máximo de 5 tentativas com falha
RATE_LIMIT_WINDOW = 900
MAX_ATTEMPTS = 5
attempts_ip: Dict[str, List[float]] = defaultdict(list)
attempts_email: Dict[str, List[float]] = defaultdict(list)

def _is_rate_limited(history: List[float], now: float) -> bool:
    history[:] = [t for t in history if now - t < RATE_LIMIT_WINDOW]
    return len(history) >= MAX_ATTEMPTS

def _record_failure(key: str, tracker: Dict[str, List[float]], now: float):
    tracker[key].append(now)

# Configuração SQLAlchemy
db_path = os.environ.get("TCC_DB_PATH", "database.db")
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

# Esquemas Pydantic
class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

app = FastAPI()

@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(dados: RegistroRequest):
    email_normalizado = dados.email.strip().lower()
    hashed = hash_senha(dados.senha)

    with SessionLocal() as db:
        existente = db.execute(
            select(Usuario).where(Usuario.email == email_normalizado)
        ).scalar_one_or_none()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )

        novo_usuario = Usuario(
            email=email_normalizado,
            senha=hashed,
            nome=dados.nome
        )
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        return {"id": novo_usuario.id}

@app.post("/login", status_code=status.HTTP_200_OK)
def login(dados: LoginRequest, request: Request):
    ip_cliente = request.client.host if request.client else "127.0.0.1"
    email_normalizado = dados.email.strip().lower()
    agora = time.time()

    if _is_rate_limited(attempts_ip[ip_cliente], agora) or _is_rate_limited(attempts_email[email_normalizado], agora):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde."
        )

    with SessionLocal() as db:
        usuario = db.execute(
            select(Usuario).where(Usuario.email == email_normalizado)
        ).scalar_one_or_none()

        if usuario:
            senha_ok = verificar_senha(dados.senha, usuario.senha)
        else:
            verificar_senha(dados.senha, DUMMY_PASSWORD_STORED)
            senha_ok = False

        if not senha_ok:
            _record_failure(ip_cliente, attempts_ip, agora)
            _record_failure(email_normalizado, attempts_email, agora)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas"
            )

        # Sucesso: limpa tentativas com falha
        attempts_ip.pop(ip_cliente, None)
        attempts_email.pop(email_normalizado, None)

        return {"id": usuario.id, "nome": usuario.nome}