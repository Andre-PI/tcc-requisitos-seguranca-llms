import os
import re
import hmac
import hashlib
import secrets
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, select, insert
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH must be defined before importing this module")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
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

_PASSWORD_MIN_LEN = 8
_PASSWORD_MAX_LEN = 128
_PBKDF2_ITERATIONS = 310_000
_SALT_BYTES = 16
_HASH_NAME = "sha256"


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=_PASSWORD_MIN_LEN, max_length=_PASSWORD_MAX_LEN)
    nome: str = Field(min_length=1, max_length=200)

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        return super().model_validate(obj, *args, **kwargs)


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=_PASSWORD_MAX_LEN)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations_s, salt_hex, hash_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        derived = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(derived, expected)
    except Exception:
        return False


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroRequest, db: Connection = Depends(get_db)):
    email = _normalize_email(payload.email)
    senha_hash = _hash_password(payload.senha)
    stmt = insert(usuarios).values(email=email, senha=senha_hash, nome=payload.nome.strip())
    try:
        result = db.execute(stmt)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já existe")
    return {"id": int(result.inserted_primary_key[0])}


@app.post("/login")
def login(payload: LoginRequest, db: Connection = Depends(get_db)):
    email = _normalize_email(payload.email)
    stmt = select(usuarios.c.id, usuarios.c.nome, usuarios.c.senha).where(usuarios.c.email == email).limit(1)
    row = db.execute(stmt).mappings().first()
    if not row or not _verify_password(payload.senha, row["senha"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    return {"id": int(row["id"]), "nome": row["nome"]}