import os
import re
import hmac
import hashlib
import secrets
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session

app = FastAPI()

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

metadata = MetaData()

usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, unique=True, nullable=False),
    Column("senha", String, nullable=False),
    Column("nome", String, nullable=False),
)

EMAIL_MAX_LEN = 254
NOME_MAX_LEN = 150
SENHA_MIN_LEN = 8
SENHA_MAX_LEN = 128
PBKDF2_ITERS = 210_000
PBKDF2_ALG = "sha256"
SALT_BYTES = 16


class RegistroIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    senha: str = Field(min_length=SENHA_MIN_LEN, max_length=SENHA_MAX_LEN)
    nome: str = Field(min_length=1, max_length=NOME_MAX_LEN)


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    senha: str = Field(min_length=1, max_length=SENHA_MAX_LEN)


def get_db() -> Session:
    return SessionLocal()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_password_policy(password: str) -> None:
    if len(password) < SENHA_MIN_LEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha inválida")
    if len(password) > SENHA_MAX_LEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha inválida")
    if password.isspace():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha inválida")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(PBKDF2_ALG, password.encode("utf-8"), salt, PBKDF2_ITERS)
    return f"pbkdf2_{PBKDF2_ALG}${PBKDF2_ITERS}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, hash_hex = stored.split("$", 3)
        if algo != f"pbkdf2_{PBKDF2_ALG}":
            return False
        iters = int(iters_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False

    derived = hashlib.pbkdf2_hmac(PBKDF2_ALG, password.encode("utf-8"), salt, iters)
    return hmac.compare_digest(derived, expected)


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn):
    email = _normalize_email(payload.email)
    _validate_password_policy(payload.senha)
    senha_hash = _hash_password(payload.senha)
    nome = payload.nome.strip()

    if not nome:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome inválido")

    with get_db() as db:
        try:
            result = db.execute(
                insert(usuarios).values(email=email, senha=senha_hash, nome=nome)
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já existe")

        user_id = result.inserted_primary_key[0]
        return {"id": int(user_id)}


@app.post("/login")
def login(payload: LoginIn):
    email = _normalize_email(payload.email)

    with get_db() as db:
        row = db.execute(
            select(usuarios.c.id, usuarios.c.senha, usuarios.c.nome).where(usuarios.c.email == email)
        ).mappings().first()

    if not row or not _verify_password(payload.senha, row["senha"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return {"id": int(row["id"]), "nome": row["nome"]}