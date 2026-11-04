import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, registry

db_path = os.environ.get("TCC_DB_PATH")
if not db_path:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite:///{db_path}", future=True)
metadata = MetaData()

usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, unique=True, nullable=False),
    Column("senha", String, nullable=False),
    Column("nome", String, nullable=False),
)

mapper_registry = registry(metadata=metadata)


class Usuario:
    pass


mapper_registry.map_imperatively(Usuario, usuarios)

app = FastAPI()


class RegistroIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr
    senha: str
    nome: str


class LoginIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr
    senha: str


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn):
    with Session(engine) as session:
        usuario = Usuario()
        usuario.email = payload.email
        usuario.senha = payload.senha
        usuario.nome = payload.nome
        session.add(usuario)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário já existe")
        session.refresh(usuario)
        return {"id": usuario.id}


@app.post("/login")
def login(payload: LoginIn):
    with Session(engine) as session:
        stmt = select(Usuario).where(Usuario.email == payload.email, Usuario.senha == payload.senha)
        usuario = session.execute(stmt).scalar_one_or_none()
        if usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return {"id": usuario.id, "nome": usuario.nome}