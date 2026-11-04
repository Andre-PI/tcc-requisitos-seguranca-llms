import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definida")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

app = FastAPI()


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


@app.post("/registro", status_code=status.HTTP_201_CREATED)
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
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já არსებობს")

    return {"id": int(user_id)}


@app.post("/login")
def login(payload: LoginIn):
    with engine.connect() as conn:
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return {"id": int(row["id"]), "nome": row["nome"]}