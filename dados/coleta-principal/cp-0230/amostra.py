from __future__ import annotations

import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

DB_PATH = os.environ["TCC_DB_PATH"]
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app = FastAPI()


class RegistroIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    senha: str
    nome: str


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    senha: str


def get_db() -> Session:
    return SessionLocal()


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn):
    db = get_db()
    try:
        result = db.execute(
            text(
                """
                INSERT INTO usuarios (email, senha, nome)
                VALUES (:email, :senha, :nome)
                """
            ),
            {"email": payload.email, "senha": payload.senha, "nome": payload.nome},
        )
        db.commit()
        return {"id": result.lastrowid}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário já existe")
    finally:
        db.close()


@app.post("/login")
def login(payload: LoginIn):
    db = get_db()
    try:
        result = db.execute(
            text(
                """
                SELECT id, nome
                FROM usuarios
                WHERE email = :email AND senha = :senha
                LIMIT 1
                """
            ),
            {"email": payload.email, "senha": payload.senha},
        )
        row = result.mappings().first()
        if row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        return {"id": row["id"], "nome": row["nome"]}
    finally:
        db.close()