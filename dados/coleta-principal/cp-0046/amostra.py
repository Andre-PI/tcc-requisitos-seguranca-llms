import os
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

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
    with SessionLocal() as db:
        try:
            result = db.execute(
                text(
                    """
                    INSERT INTO usuarios (email, senha, nome)
                    VALUES (:email, :senha, :nome)
                    """
                ),
                {"email": payload.email, "senha": payload.senha, "nome": payload.nome},
            )
            db.commit()
            user_id = result.lastrowid
            return {"id": int(user_id)}
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado")


@app.post("/login")
def login(payload: LoginIn):
    with SessionLocal() as db:
        result = db.execute(
            text(
                """
                SELECT id, nome
                FROM usuarios
                WHERE email = :email AND senha = :senha
                LIMIT 1
                """
            ),
            {"email": payload.email, "senha": payload.senha},
        )
        row = result.mappings().first()
        if row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        return {"id": int(row["id"]), "nome": row["nome"]}