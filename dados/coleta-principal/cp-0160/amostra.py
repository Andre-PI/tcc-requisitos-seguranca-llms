import os
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definida")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

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
    with SessionLocal() as session:
        try:
            result = session.execute(
                text(
                    "INSERT INTO usuarios (email, senha, nome) "
                    "VALUES (:email, :senha, :nome)"
                ),
                {"email": payload.email, "senha": payload.senha, "nome": payload.nome},
            )
            session.commit()
            return {"id": result.lastrowid}
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email já cadastrado")


@app.post("/login")
def login(payload: LoginIn):
    with SessionLocal() as session:
        result = session.execute(
            text(
                "SELECT id, nome, senha "
                "FROM usuarios "
                "WHERE email = :email "
                "LIMIT 1"
            ),
            {"email": payload.email},
        ).mappings().first()

        if not result or result["senha"] != payload.senha:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="credenciais inválidas")

        return {"id": result["id"], "nome": result["nome"]}