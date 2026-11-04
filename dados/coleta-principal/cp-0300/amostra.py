import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, insert
from sqlalchemy.orm import sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
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


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


@app.post("/registro", status_code=201)
def registro(payload: RegistroRequest):
    with SessionLocal() as session:
        result = session.execute(
            insert(usuarios).values(
                email=payload.email,
                senha=payload.senha,
                nome=payload.nome,
            )
        )
        session.commit()
        return {"id": result.inserted_primary_key[0]}


@app.post("/login")
def login(payload: LoginRequest):
    with SessionLocal() as session:
        stmt = select(usuarios.c.id, usuarios.c.nome).where(
            usuarios.c.email == payload.email,
            usuarios.c.senha == payload.senha,
        )
        row = session.execute(stmt).first()
        if row is None:
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
        return {"id": row.id, "nome": row.nome}