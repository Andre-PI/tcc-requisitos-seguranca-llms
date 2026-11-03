import os
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
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
    with SessionLocal() as session:
        stmt = insert(usuarios).values(
            email=payload.email,
            senha=payload.senha,
            nome=payload.nome,
        )
        try:
            result = session.execute(stmt)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado")

        inserted_id = result.inserted_primary_key[0]
        return {"id": inserted_id}


@app.post("/login")
def login(payload: LoginIn):
    with SessionLocal() as session:
        stmt = select(usuarios.c.id, usuarios.c.nome).where(
            usuarios.c.email == payload.email,
            usuarios.c.senha == payload.senha,
        )
        result = session.execute(stmt).first()

        if result is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

        return {"id": result.id, "nome": result.nome}