import os
import hashlib
import hmac
from typing import Generator
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Integer, String, select
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, Session, sessionmaker

db_path = os.getenv("TCC_DB_PATH", "database.db")
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    senha: Mapped[str] = mapped_column(String, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    iterations = 600_000
    hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{salt.hex()}${iterations}${hash_bytes.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_hex, iterations_str, hash_hex = hashed_password.split("$")
        salt = bytes.fromhex(salt_hex)
        iterations = int(iterations_str)
        hash_bytes = bytes.fromhex(hash_hex)
        candidate = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(candidate, hash_bytes)
    except Exception:
        return False


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


app = FastAPI()


@app.post("/registro", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def registro(dados: RegistroRequest, db: Session = Depends(get_db)):
    stmt = select(Usuario).where(Usuario.email == dados.email)
    usuario_existente = db.execute(stmt).scalar_one_or_none()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado."
        )

    novo_usuario = Usuario(
        email=dados.email,
        senha=hash_password(dados.senha),
        nome=dados.nome
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return {"id": novo_usuario.id}


@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    stmt = select(Usuario).where(Usuario.email == dados.email)
    usuario = db.execute(stmt).scalar_one_or_none()

    dummy_hash = "00" * 16 + "$600000$" + "00" * 32
    if usuario is None:
        verify_password(dados.senha, dummy_hash)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas."
        )

    if not verify_password(dados.senha, usuario.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas."
        )

    return {"id": usuario.id, "nome": usuario.nome}