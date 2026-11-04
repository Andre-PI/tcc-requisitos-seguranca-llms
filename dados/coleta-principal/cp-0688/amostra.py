import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definida")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

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


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroRequest):
    with SessionLocal() as session:
        try:
            result = session.execute(
                insert(usuarios).values(
                    email=payload.email,
                    senha=payload.senha,
                    nome=payload.nome,
                )
            )
            session.commit()
            return {"id": result.inserted_primary_key[0]}
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário já existe")


@app.post("/login")
def login(payload: LoginRequest):
    with SessionLocal() as session:
        stmt = select(usuarios.c.id, usuarios.c.nome).where(
            usuarios.c.email == payload.email,
            usuarios.c.senha == payload.senha,
        )
        row = session.execute(stmt).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        return {"id": row.id, "nome": row.nome}