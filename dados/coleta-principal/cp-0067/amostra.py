import os
import hmac
import hashlib
import secrets
from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definido")
    return db_path


def _build_engine() -> Engine:
    db_path = _get_db_path()
    return create_engine(
        f"sqlite+pysqlite:///{db_path}",
        future=True,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )


engine = _build_engine()


class RegistroIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    senha: Annotated[str, Field(min_length=8, max_length=128)]
    nome: Annotated[str, Field(min_length=1, max_length=120)]


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    senha: Annotated[str, Field(min_length=1, max_length=128)]


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 210000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations_s, salt_hex, hash_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn):
    hashed = _hash_password(payload.senha)
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO usuarios (email, senha, nome)
                    VALUES (:email, :senha, :nome)
                    """
                ),
                {"email": payload.email, "senha": hashed, "nome": payload.nome},
            )
            user_id = result.lastrowid
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já cadastrado")
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno")
    return {"id": int(user_id)}


@app.post("/login")
def login(payload: LoginIn):
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, email, senha, nome
                    FROM usuarios
                    WHERE email = :email
                    LIMIT 1
                    """
                ),
                {"email": payload.email},
            ).mappings().first()
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno")

    if not row or not _verify_password(payload.senha, row["senha"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return {"id": int(row["id"]), "nome": row["nome"]}