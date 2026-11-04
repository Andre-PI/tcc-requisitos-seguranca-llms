import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, text

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///test.db")
if not db_path.startswith("sqlite:///"):
    db_url = f"sqlite:///{db_path}"
else:
    db_url = db_path

engine = create_engine(db_url, connect_args={"check_same_thread": False})

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
            text("INSERT INTO usuarios (email, senha, nome) VALUES (:email, :senha, :nome)"),
            {"email": dados.email, "senha": dados.senha, "nome": dados.nome},
        )
        user_id = result.lastrowid
    return {"id": user_id}


@app.post("/login", status_code=status.HTTP_200_OK, response_model=LoginResponse)
def login(dados: LoginRequest):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, nome FROM usuarios WHERE email = :email AND senha = :senha"),
            {"email": dados.email, "senha": dados.senha},
        ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    return {"id": result.id, "nome": result.nome}