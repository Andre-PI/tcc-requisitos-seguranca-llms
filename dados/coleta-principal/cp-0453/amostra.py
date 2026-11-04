import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

db_path = os.environ.get("TCC_DB_PATH")
if not db_path:
    raise RuntimeError("TCC_DB_PATH não definido")

if db_path.startswith("sqlite:///") or db_path.startswith("sqlite://"):
    database_url = db_path
else:
    database_url = f"sqlite:///{db_path}"

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False},
    future=True,
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já existe")

    return {"id": int(user_id)}


@app.post("/login")
def login(payload: LoginIn):
    with engine.begin() as conn:
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

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return {"id": int(row["id"]), "nome": row["nome"]}