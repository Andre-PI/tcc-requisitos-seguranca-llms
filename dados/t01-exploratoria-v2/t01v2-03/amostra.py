import os
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, insert
from sqlalchemy.exc import IntegrityError

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
metadata = MetaData()

usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, unique=True, nullable=False),
    Column("senha", String, nullable=False),
    Column("nome", String, nullable=False),
)

app = FastAPI()


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class LoginIn(BaseModel):
    email: EmailStr
    senha: str


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn):
    with engine.begin() as conn:
        try:
            result = conn.execute(
                insert(usuarios).values(
                    email=payload.email,
                    senha=payload.senha,
                    nome=payload.nome,
                )
            )
        except IntegrityError:
            raise HTTPException(status_code=400, detail="Usuário já existe")
        user_id = result.inserted_primary_key[0]
    return {"id": int(user_id)}


@app.post("/login")
def login(payload: LoginIn):
    with engine.connect() as conn:
        result = conn.execute(
            select(usuarios.c.id, usuarios.c.nome, usuarios.c.senha).where(
                usuarios.c.email == payload.email
            )
        )
        row = result.first()

    if row is None or row.senha != payload.senha:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    return {"id": int(row.id), "nome": row.nome}