from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

if DB_PATH.startswith("sqlite:///") or DB_PATH.startswith("sqlite:////"):
    DATABASE_URL = DB_PATH
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app = FastAPI()


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class LoginIn(BaseModel):
    email: EmailStr
    senha: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str


class RegistroOut(BaseModel):
    id: int


@app.post("/registro", status_code=201, response_model=RegistroOut)
def registro(payload: RegistroIn):
    with SessionLocal() as session:
        try:
            result = session.execute(
                text(
                    """
                    INSERT INTO usuarios (email, senha, nome)
                    VALUES (:email, :senha, :nome)
                    """
                ),
                {"email": str(payload.email), "senha": payload.senha, "nome": payload.nome},
            )
            session.commit()
            user_id = result.lastrowid
            return {"id": int(user_id)}
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=400, detail="Usuário já existe")


@app.post("/login", response_model=UsuarioOut)
def login(payload: LoginIn):
    with SessionLocal() as session:
        result = session.execute(
            text(
                """
                SELECT id, nome
                FROM usuarios
                WHERE email = :email AND senha = :senha
                LIMIT 1
                """
            ),
            {"email": str(payload.email), "senha": payload.senha},
        ).mappings().first()

        if not result:
            raise HTTPException(status_code=401, detail="Credenciais inválidas")

        return {"id": int(result["id"]), "nome": result["nome"]}