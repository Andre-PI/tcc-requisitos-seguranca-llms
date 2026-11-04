from __future__ import annotations

import os
import re
import hmac
import hashlib
import secrets
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session


app = FastAPI()

_DB_PATH = os.environ.get("TCC_DB_PATH")
if not _DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definida")

_DATABASE_URL = f"sqlite:///{_DB_PATH}"
engine: Engine = create_engine(
    _DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
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

PASSWORD_HASH_ALGO = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 210_000
PASSWORD_SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 256
MAX_NAME_LENGTH = 120


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    nome: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class IdResponse(BaseModel):
    id: int


class LoginResponse(BaseModel):
    id: int
    nome: str


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_password_policy(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Senha inválida",
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Senha inválida",
        )


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"{PASSWORD_HASH_ALGO}${PASSWORD_ITERATIONS}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations_str, salt_hex, hash_hex = stored.split("$", 3)
        if algo != PASSWORD_HASH_ALGO:
            return False
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(derived, expected)


def _get_session() -> Session:
    return SessionLocal()


@app.post("/registro", response_model=IdResponse, status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn) -> IdResponse:
    email = _normalize_email(str(payload.email))
    _validate_password_policy(payload.senha)
    nome = payload.nome.strip()

    if not nome:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nome inválido",
        )

    hashed_password = _hash_password(payload.senha)

    with _get_session() as session:
        try:
            stmt = insert(usuarios).values(email=email, senha=hashed_password, nome=nome)
            result = session.execute(stmt)
            session.commit()
            inserted_id = result.inserted_primary_key[0]
            return IdResponse(id=int(inserted_id))
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Usuário já cadastrado",
            )


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginIn) -> LoginResponse:
    email = _normalize_email(str(payload.email))

    with _get_session() as session:
        stmt = select(usuarios.c.id, usuarios.c.nome, usuarios.c.senha).where(usuarios.c.email == email)
        row = session.execute(stmt).mappings().first()

        if not row or not _verify_password(payload.senha, row["senha"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return LoginResponse(id=int(row["id"]), nome=str(row["nome"]))