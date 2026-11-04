import os
import re
import hmac
import hashlib
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, select, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
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
PBKDF2_ITERATIONS = 210000
PBKDF2_ALGORITHM = "sha256"
HASH_PREFIX = "pbkdf2_sha256"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"{HASH_PREFIX}${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        prefix, iterations_s, salt_hex, digest_hex = stored.split("$", 3)
        if prefix != HASH_PREFIX:
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except Exception:
        return False

    candidate = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate, expected)


class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=PASSWORD_MIN_LEN, max_length=PASSWORD_MAX_LEN)
    nome: str = Field(min_length=1, max_length=255)

    @classmethod
    def model_validate(cls, *args, **kwargs):
        obj = super().model_validate(*args, **kwargs)
        if not re.search(r"[A-Za-z]", obj.senha) or not re.search(r"\d", obj.senha):
            raise ValueError("senha fraca")
        return obj


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=PASSWORD_MAX_LEN)


class RegistroOut(BaseModel):
    id: int


class LoginOut(BaseModel):
    id: int
    nome: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/registro", response_model=RegistroOut, status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn, db: Session = Depends(get_db)):
    senha_hash = _hash_password(payload.senha)
    stmt = insert(usuarios).values(
        email=payload.email.lower(),
        senha=senha_hash,
        nome=payload.nome.strip(),
    )
    try:
        result = db.execute(stmt)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="usuario ja existe")

    user_id = result.inserted_primary_key[0]
    return {"id": int(user_id)}


@app.post("/login", response_model=LoginOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    stmt = select(usuarios.c.id, usuarios.c.nome, usuarios.c.senha).where(
        usuarios.c.email == payload.email.lower()
    )
    row = db.execute(stmt).mappings().first()

    if not row or not _verify_password(payload.senha, row["senha"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="credenciais invalidas")

    return {"id": int(row["id"]), "nome": row["nome"]}