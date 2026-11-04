import os
import hmac
import hashlib
import secrets
import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String
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


PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS
    )
    return f"{salt}:{dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected_dk = stored_hash.split(":")
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            PBKDF2_ITERATIONS
        )
        return hmac.compare_digest(dk.hex(), expected_dk)
    except Exception:
        return False


DUMMY_SALT = secrets.token_hex(16)
DUMMY_HASH = f"{DUMMY_SALT}:" + hashlib.pbkdf2_hmac(
    "sha256",
    b"dummy_password",
    DUMMY_SALT.encode("utf-8"),
    PBKDF2_ITERATIONS
).hex()

login_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
LOCKOUT_WINDOW = 300


def check_rate_limit(key: str) -> bool:
    now = time.time()
    attempts = [t for t in login_attempts[key] if now - t < LOCKOUT_WINDOW]
    login_attempts[key] = attempts
    return len(attempts) < MAX_ATTEMPTS


def record_attempt(key: str):
    login_attempts[key].append(time.time())


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
    db = SessionLocal()
    try:
        usuario_existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já registrado"
            )

        hashed = hash_password(dados.senha)
        novo_usuario = Usuario(
            email=dados.email,
            senha=hashed,
            nome=dados.nome
        )
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        return {"id": novo_usuario.id}
    finally:
        db.close()


@app.post("/login", status_code=status.HTTP_200_OK)
def login(dados: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    ip_key = f"ip:{client_ip}"
    account_key = f"account:{dados.email}"

    if not check_rate_limit(ip_key) or not check_rate_limit(account_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde."
        )

    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()
        if usuario:
            valid = verify_password(dados.senha, usuario.senha)
        else:
            verify_password(dados.senha, DUMMY_HASH)
            valid = False

        if not valid:
            record_attempt(ip_key)
            record_attempt(account_key)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas"
            )

        login_attempts.pop(account_key, None)
        return {"id": usuario.id, "nome": usuario.nome}
    finally:
        db.close()