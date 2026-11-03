import os
import re
import hmac
import hashlib
import secrets
from contextlib import contextmanager
from typing import Generator

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, select, insert
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
    future=True,
)

metadata = MetaData()
usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", Text, nullable=False, unique=True),
    Column("senha", Text, nullable=False),
    Column("nome", Text, nullable=False),
)

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PBKDF2_ITERATIONS = 310_000
SALT_BYTES = 16
HASH_NAME = "sha256"

PASSWORD_POLICY = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).+$")


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    nome: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class RegistroResponse(BaseModel):
    id: int


class LoginResponse(BaseModel):
    id: int
    nome: str


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_password_strength(password: str) -> None:
    if not PASSWORD_POLICY.match(password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Senha fraca",
        )


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        HASH_NAME,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_{HASH_NAME}${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations_s, salt_hex, digest_hex = stored.split("$", 3)
        if algo != f"pbkdf2_{HASH_NAME}":
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except Exception:
        return False

    candidate = hashlib.pbkdf2_hmac(
        HASH_NAME,
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate, expected)


@contextmanager
def get_connection() -> Generator[Connection, None, None]:
    with engine.begin() as conn:
        yield conn


@app.post("/registro", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroRequest, conn: Connection = Depends(get_connection)):
    email = _normalize_email(payload.email)
    _validate_password_strength(payload.senha)
    senha_hash = _hash_password(payload.senha)
    nome = payload.nome.strip()

    stmt = insert(usuarios).values(email=email, senha=senha_hash, nome=nome)
    try:
        result = conn.execute(stmt)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado",
        )

    inserted_id = result.inserted_primary_key[0]
    return {"id": int(inserted_id)}


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, conn: Connection = Depends(get_connection)):
    email = _normalize_email(payload.email)

    stmt = select(usuarios.c.id, usuarios.c.nome, usuarios.c.senha).where(usuarios.c.email == email)
    row = conn.execute(stmt).mappings().first()

    if not row or not _verify_password(payload.senha, row["senha"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return {"id": int(row["id"]), "nome": row["nome"]}