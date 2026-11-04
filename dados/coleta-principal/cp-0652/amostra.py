import os
import hmac
import hashlib
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, select, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from passlib.context import CryptContext


DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

metadata = MetaData()
usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", Text, unique=True, nullable=False),
    Column("senha", Text, nullable=False),
    Column("nome", Text, nullable=False),
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8, max_length=256)
    nome: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=256)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroRequest):
    senha_hash = hash_password(payload.senha)
    with SessionLocal() as session:
        try:
            result = session.execute(
                insert(usuarios).values(
                    email=payload.email.lower().strip(),
                    senha=senha_hash,
                    nome=payload.nome.strip(),
                )
            )
            session.commit()
            user_id = result.inserted_primary_key[0]
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já cadastrado")
    return {"id": user_id}


@app.post("/login")
def login(payload: LoginRequest):
    with SessionLocal() as session:
        stmt = select(usuarios.c.id, usuarios.c.nome, usuarios.c.senha).where(
            usuarios.c.email == payload.email.lower().strip()
        )
        row = session.execute(stmt).first()

    if not row or not verify_password(payload.senha, row.senha):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return {"id": row.id, "nome": row.nome}