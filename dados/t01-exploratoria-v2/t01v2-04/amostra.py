import os
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import hashlib

TCC_DB_PATH = os.environ["TCC_DB_PATH"]
DATABASE_URL = f"sqlite:///{TCC_DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()

usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, unique=True, nullable=False),
    Column("senha", String, nullable=False),
    Column("nome", String, nullable=False),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

app = FastAPI()

class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str

class RegistroResponse(BaseModel):
    id: int

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

class LoginResponse(BaseModel):
    id: int
    nome: str

def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()

@app.post("/registro", status_code=status.HTTP_201_CREATED, response_model=RegistroResponse)
def registro(data: RegistroRequest):
    senha_hash = hash_senha(data.senha)
    with SessionLocal() as session:
        stmt = usuarios.insert().values(email=data.email, senha=senha_hash, nome=data.nome)
        try:
            result = session.execute(stmt)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")
        user_id = result.inserted_primary_key[0]
    return {"id": user_id}

@app.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    senha_hash = hash_senha(data.senha)
    with SessionLocal() as session:
        stmt = select(usuarios.c.id, usuarios.c.nome).where(usuarios.c.email == data.email, usuarios.c.senha == senha_hash)
        result = session.execute(stmt).first()
        if not result:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        user_id, nome = result
    return {"id": user_id, "nome": nome}