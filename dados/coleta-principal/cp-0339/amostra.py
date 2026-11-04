import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine: Engine = create_engine(DATABASE_URL, future=True)
metadata = MetaData()

usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, nullable=False, unique=True),
    Column("senha", String, nullable=False),
    Column("nome", String, nullable=False),
)

app = FastAPI()


class RegistroIn(BaseModel):
    email: EmailStr
    senha: Annotated[str, Field(min_length=1)]
    nome: Annotated[str, Field(min_length=1)]


class LoginIn(BaseModel):
    email: EmailStr
    senha: Annotated[str, Field(min_length=1)]


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn):
    stmt = insert(usuarios).values(
        email=payload.email,
        senha=payload.senha,
        nome=payload.nome,
    )

    try:
        with engine.begin() as conn:
            result = conn.execute(stmt)
            user_id = result.inserted_primary_key[0]
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email já cadastrado")

    return {"id": user_id}


@app.post("/login")
def login(payload: LoginIn):
    stmt = select(usuarios.c.id, usuarios.c.nome).where(
        usuarios.c.email == payload.email,
        usuarios.c.senha == payload.senha,
    )

    with engine.connect() as conn:
        row = conn.execute(stmt).first()

    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return {"id": row.id, "nome": row.nome}