import os
import re
import hmac
import hashlib
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

app = FastAPI()

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

db_url = f"sqlite:///{Path(DB_PATH).as_posix()}"
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
    Column("email", String, unique=True, nullable=False),
    Column("senha", String, nullable=False),
    Column("nome", String, nullable=False),
)

EMAIL_MAX_LEN = 254
NOME_MAX_LEN = 150
SENHA_MIN_LEN = 8
SENHA_MAX_LEN = 128

PASSWORD_SCHEME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 310_000
SALT_BYTES = 16
HASH_BYTES = 32


class RegistroIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    email: EmailStr
    senha: str = Field(min_length=SENHA_MIN_LEN, max_length=SENHA_MAX_LEN)
    nome: str = Field(min_length=1, max_length=NOME_MAX_LEN)


class LoginIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    email: EmailStr
    senha: str = Field(min_length=1, max_length=SENHA_MAX_LEN)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_password_policy(password: str) -> None:
    if len(password) < SENHA_MIN_LEN:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Senha inválida")
    if len(password) > SENHA_MAX_LEN:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Senha inválida")
    if password.isspace():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Senha inválida")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=HASH_BYTES,
    )
    return f"{PASSWORD_SCHEME}${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations_s, salt_hex, hash_hex = stored.split("$", 3)
        if scheme != PASSWORD_SCHEME:
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=len(expected),
    )
    return hmac.compare_digest(candidate, expected)


def _get_user_by_email(db, email: str):
    stmt = select(
        usuarios.c.id,
        usuarios.c.email,
        usuarios.c.senha,
        usuarios.c.nome,
    ).where(usuarios.c.email == email)
    return db.execute(stmt).mappings().first()


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn):
    email = _normalize_email(payload.email)
    _validate_password_policy(payload.senha)
    nome = payload.nome.strip()

    if not nome:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nome inválido")

    senha_hash = _hash_password(payload.senha)

    with SessionLocal() as db:
        try:
            result = db.execute(
                insert(usuarios).values(email=email, senha=senha_hash, nome=nome)
            )
            db.commit()
            return {"id": int(result.inserted_primary_key[0])}
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já existe")


@app.post("/login")
def login(payload: LoginIn):
    email = _normalize_email(payload.email)

    with SessionLocal() as db:
        user = _get_user_by_email(db, email)

        if not user or not _verify_password(payload.senha, user["senha"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

        return {"id": int(user["id"]), "nome": user["nome"]}