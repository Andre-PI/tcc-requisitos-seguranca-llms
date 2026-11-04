import os
import re
import hmac
import hashlib
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr, ConfigDict
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, select, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

db_url = f"sqlite:///{Path(DB_PATH)}"
engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

metadata = MetaData()
usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", Text, unique=True, nullable=False),
    Column("senha", Text, nullable=False),
    Column("nome", Text, nullable=False),
)

app = FastAPI()


class RegistroRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    senha: SecretStr = Field(min_length=8, max_length=256)
    nome: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    senha: SecretStr = Field(min_length=1, max_length=256)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_nome(nome: str) -> str:
    return re.sub(r"\s+", " ", nome).strip()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"pbkdf2_sha256$200000${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations_str, salt_hex, hash_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False


def _get_user_by_email(session, email: str):
    stmt = select(usuarios.c.id, usuarios.c.email, usuarios.c.senha, usuarios.c.nome).where(usuarios.c.email == email)
    return session.execute(stmt).mappings().first()


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroRequest):
    email = _normalize_email(str(payload.email))
    nome = _normalize_nome(payload.nome)
    senha = payload.senha.get_secret_value()

    if not nome:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dados inválidos")

    hashed = _hash_password(senha)

    with SessionLocal() as session:
        try:
            result = session.execute(
                insert(usuarios).values(email=email, senha=hashed, nome=nome)
            )
            session.commit()
            return {"id": result.inserted_primary_key[0]}
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já existe")


@app.post("/login")
def login(payload: LoginRequest):
    email = _normalize_email(str(payload.email))
    senha = payload.senha.get_secret_value()

    with SessionLocal() as session:
        user = _get_user_by_email(session, email)
        if not user or not _verify_password(senha, user["senha"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        return {"id": user["id"], "nome": user["nome"]}