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

DB_PATH = os.environ.get("TCC_DB_PATH", "usuarios.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)


# Algoritmo de hash de senha PBKDF2-HMAC-SHA256 com fator de custo configurável
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt, stored_hash = password_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt_bytes = bytes.fromhex(salt)
        stored_bytes = bytes.fromhex(stored_hash)
    except Exception:
        return False

    computed = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), salt_bytes, iterations
    )
    return hmac.compare_digest(computed, stored_bytes)


# Hash fictício para mitigar ataques de temporização quando o usuário não existir
DUMMY_HASH = hash_password("senha_ficticia_mitigacao_temporizacao")

# Rate Limiting em memória (tentativas por IP e por conta de e-mail)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 minutos

ip_attempts: Dict[str, List[float]] = defaultdict(list)
account_attempts: Dict[str, List[float]] = defaultdict(list)


def is_rate_limited(ip: str, email: str) -> bool:
    now = time.time()
    clean_ip = [t for t in ip_attempts[ip] if now - t < WINDOW_SECONDS]
    clean_acc = [t for t in account_attempts[email] if now - t < WINDOW_SECONDS]
    ip_attempts[ip] = clean_ip
    account_attempts[email] = clean_acc

    return len(clean_ip) >= MAX_ATTEMPTS or len(clean_acc) >= MAX_ATTEMPTS


def record_failed_attempt(ip: str, email: str) -> None:
    now = time.time()
    ip_attempts[ip].append(now)
    account_attempts[email].append(now)


def clear_failed_attempts(ip: str, email: str) -> None:
    account_attempts.pop(email, None)


app = FastAPI()


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(dados: RegistroRequest):
    email_clean = dados.email.lower().strip()
    with SessionLocal() as db:
        stmt = select(Usuario).where(Usuario.email == email_clean)
        usuario_existente = db.execute(stmt).scalar_one_or_none()
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ja cadastrado",
            )

        hashed = hash_password(dados.senha)
        novo_usuario = Usuario(
            email=email_clean,
            senha=hashed,
            nome=dados.nome,
        )
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        return {"id": novo_usuario.id}


@app.post("/login", status_code=status.HTTP_200_OK)
def login(dados: LoginRequest, request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    email_clean = dados.email.lower().strip()

    if is_rate_limited(ip, email_clean):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
        )

    with SessionLocal() as db:
        stmt = select(Usuario).where(Usuario.email == email_clean)
        usuario = db.execute(stmt).scalar_one_or_none()

        target_hash = usuario.senha if usuario else DUMMY_HASH
        is_valid = verify_password(dados.senha, target_hash)

        if not usuario or not is_valid:
            record_failed_attempt(ip, email_clean)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas",
            )

        clear_failed_attempts(ip, email_clean)
        return {"id": usuario.id, "nome": usuario.nome}