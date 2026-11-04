import os
import re
import hmac
import hashlib
import secrets
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, insert
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH must be defined before importing this module")

db_file = Path(DB_PATH)
engine: Engine = create_engine(
    f"sqlite:///{db_file}",
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
    future=True,
)

metadata = MetaData()
usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, nullable=False, unique=True),
    Column("senha", String, nullable=False),
    Column("nome", String, nullable=False),
)

PASSWORD_MIN_LEN = 8
PASSWORD_MAX_LEN = 128
PBKDF2_ITERATIONS = 210_000
SALT_BYTES = 16
HASH_NAME = "sha256"


class RegistroRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    senha: str = Field(min_length=PASSWORD_MIN_LEN, max_length=PASSWORD_MAX_LEN)
    nome: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    senha: str = Field(min_length=1, max_length=PASSWORD_MAX_LEN)


def _validate_password_policy(password: str) -> None:
    if len(password) < PASSWORD_MIN_LEN or len(password) > PASSWORD_MAX_LEN:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dados inválidos")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dados inválidos")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_{HASH_NAME}${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations_s, salt_hex, hash_hex = stored.split("$", 3)
        if scheme != f"pbkdf2_{HASH_NAME}":
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False

    candidate = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def get_connection():
    with engine.begin() as conn:
        yield conn


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroRequest, conn: Annotated[Connection, Depends(get_connection)]):
    _validate_password_policy(payload.senha)
    hashed = _hash_password(payload.senha)
    stmt = insert(usuarios).values(email=str(payload.email).lower(), senha=hashed, nome=payload.nome)
    try:
        result = conn.execute(stmt)
        user_id = result.inserted_primary_key[0]
        return {"id": int(user_id)}
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já cadastrado")


@app.post("/login")
def login(payload: LoginRequest, conn: Annotated[Connection, Depends(get_connection)]):
    stmt = select(usuarios.c.id, usuarios.c.nome, usuarios.c.senha).where(usuarios.c.email == str(payload.email).lower())
    row = conn.execute(stmt).mappings().first()
    if not row or not _verify_password(payload.senha, row["senha"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    return {"id": int(row["id"]), "nome": row["nome"]}