import os
from typing import Generator

from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import IntegrityError

db_path = os.environ.get("TCC_DB_PATH")
if not db_path:
    raise RuntimeError("TCC_DB_PATH não definido")

engine: Engine = create_engine(f"sqlite:///{db_path}", future=True)
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


def get_connection() -> Generator[Connection, None, None]:
    with engine.begin() as conn:
        yield conn


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class LoginIn(BaseModel):
    email: EmailStr
    senha: str


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn, conn: Connection = Depends(get_connection)):
    stmt = usuarios.insert().values(
        email=payload.email,
        senha=payload.senha,
        nome=payload.nome,
    )
    try:
        result = conn.execute(stmt)
        user_id = result.inserted_primary_key[0]
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email já cadastrado")
    return {"id": user_id}


@app.post("/login")
def login(payload: LoginIn, conn: Connection = Depends(get_connection)):
    stmt = select(usuarios.c.id, usuarios.c.nome).where(
        usuarios.c.email == payload.email,
        usuarios.c.senha == payload.senha,
    )
    result = conn.execute(stmt).mappings().first()
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="credenciais inválidas")
    return {"id": result["id"], "nome": result["nome"]}