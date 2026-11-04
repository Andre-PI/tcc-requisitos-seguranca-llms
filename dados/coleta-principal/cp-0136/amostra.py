import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, text

db_path = os.environ.get("TCC_DB_PATH")
engine = create_engine(f"sqlite:///{db_path}")

app = FastAPI()


class RegistroRequest(BaseModel):
    email: str
    senha: str
    nome: str


class RegistroResponse(BaseModel):
    id: int


class LoginRequest(BaseModel):
    email: str
    senha: str


class LoginResponse(BaseModel):
    id: int
    nome: str


@app.post("/registro", status_code=status.HTTP_201_CREATED, response_model=RegistroResponse)
def registro(dados: RegistroRequest):
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT id FROM usuarios WHERE email = :email"),
            {"email": dados.email},
        ).fetchone()
        if result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ja cadastrado",
            )
        result = conn.execute(
            text(
                "INSERT INTO usuarios (email, senha, nome) VALUES (:email, :senha, :nome)"
            ),
            {"email": dados.email, "senha": dados.senha, "nome": dados.nome},
        )
        return {"id": result.lastrowid}


@app.post("/login", status_code=status.HTTP_200_OK, response_model=LoginResponse)
def login(dados: LoginRequest):
    with engine.connect() as conn:
        user = conn.execute(
            text("SELECT id, nome FROM usuarios WHERE email = :email AND senha = :senha"),
            {"email": dados.email, "senha": dados.senha},
        ).fetchone()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas",
            )
        return {"id": user.id, "nome": user.nome}