import os
import re
import hmac
import hashlib
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, select, insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(
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

PASSWORD_MIN_LEN = 8
PASSWORD_MAX_LEN = 128
SALT_BYTES = 16
PBKDF2_ITERS = 210_000


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_password_policy(password: str) -> None:
    if not (PASSWORD_MIN_LEN <= len(password) <= PASSWORD_MAX_LEN):
        raise HTTPException(status_code=400, detail="Senha inválida")
    if password.strip() != password:
        raise HTTPException(status_code=400, detail="Senha inválida")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="Senha inválida")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERS)
    return f"pbkdf2_sha256${PBKDF2_ITERS}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, hash_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False
    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return hmac.compare_digest(computed, expected)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RegistroRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    senha: str = Field(min_length=PASSWORD_MIN_LEN, max_length=PASSWORD_MAX_LEN)
    nome: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    senha: str = Field(min_length=1, max_length=PASSWORD_MAX_LEN)


class RegistroResponse(BaseModel):
    id: int


class LoginResponse(BaseModel):
    id: int
    nome: str


def _create_user(db: Session, email: str, senha: str, nome: str) -> int:
    _validate_password_policy(senha)
    stmt = insert(usuarios).values(
        email=_normalize_email(email),
        senha=_hash_password(senha),
        nome=nome.strip(),
    )
    try:
        result = db.execute(stmt)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Usuário já cadastrado")
    return int(result.inserted_primary_key[0])


def _authenticate_user(db: Session, email: str, senha: str):
    stmt = select(usuarios.c.id, usuarios.c.nome, usuarios.c.senha).where(
        usuarios.c.email == _normalize_email(email)
    )
    row = db.execute(stmt).mappings().first()
    if not row or not _verify_password(senha, row["senha"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    return {"id": int(row["id"]), "nome": row["nome"]}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/registro", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroRequest, db: Session = Depends(get_db)):
    user_id = _create_user(db, payload.email, payload.senha, payload.nome)
    return {"id": user_id}


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return _authenticate_user(db, payload.email, payload.senha)