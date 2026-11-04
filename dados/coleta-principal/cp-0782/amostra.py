import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definida")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

app = FastAPI()


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class LoginIn(BaseModel):
    email: EmailStr
    senha: str


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
        return {"id": user_id}
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Usuário já existe")


@app.post("/login")
def login(payload: LoginIn):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, nome, senha
                FROM usuarios
                WHERE email = :email
                """
            ),
            {"email": payload.email},
        ).fetchone()

    if row is None or row.senha != payload.senha:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    return {"id": row.id, "nome": row.nome}