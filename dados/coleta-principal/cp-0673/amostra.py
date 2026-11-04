import os
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker

db_path = os.environ.get("TCC_DB_PATH")
if not db_path:
    raise RuntimeError("TCC_DB_PATH não definida")

db_url = f"sqlite:///{db_path}"
engine = create_engine(db_url, connect_args={"check_same_thread": False}, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)


app = FastAPI()


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroRequest):
    with SessionLocal() as session:
        usuario = Usuario(email=payload.email, senha=payload.senha, nome=payload.nome)
        session.add(usuario)
        try:
            session.commit()
            session.refresh(usuario)
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário já existe")
        return {"id": usuario.id}


@app.post("/login")
def login(payload: LoginRequest):
    with SessionLocal() as session:
        stmt = select(Usuario).where(Usuario.email == payload.email, Usuario.senha == payload.senha)
        usuario: Optional[Usuario] = session.execute(stmt).scalar_one_or_none()
        if usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        return {"id": usuario.id, "nome": usuario.nome}