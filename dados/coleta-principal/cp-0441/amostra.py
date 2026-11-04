from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine: Engine = create_engine(DATABASE_URL, future=True)

app = FastAPI()


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


@app.post("/registro", status_code=201)
def registro(payload: RegistroIn):
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO usuarios (email, senha, nome)
                    VALUES (:email, :senha, :nome)
                    """
                ),
                {"email": payload.email, "senha": payload.senha, "nome": payload.nome},
            )
            user_id = result.lastrowid
            return {"id": int(user_id)}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Usuário já existente")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno")


@app.post("/login")
def login(payload: LoginIn):
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, nome
                    FROM usuarios
                    WHERE email = :email AND senha = :senha
                    """
                ),
                {"email": payload.email, "senha": payload.senha},
            ).mappings().first()

            if row is None:
                raise HTTPException(status_code=401, detail="Credenciais inválidas")

            return {"id": int(row["id"]), "nome": row["nome"]}
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno")