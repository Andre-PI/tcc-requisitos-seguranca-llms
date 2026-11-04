import hashlib
import hmac
import os
import secrets
from typing import Generator
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column, Session

DB_PATH = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not DB_PATH.startswith("sqlite:///"):
    DB_PATH = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DB_PATH,
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


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    )
    return f"{salt}:{dk.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        salt, dk_hex = stored_hash.split(":", 1)
        expected_dk = bytes.fromhex(dk_hex)
        actual_dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        )
        return hmac.compare_digest(actual_dk, expected_dk)
    except Exception:
        return False


class UsuarioRegistro(BaseModel):
    email: EmailStr
    senha: str
    nome: str


class RegistroResposta(BaseModel):
    id: int


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


class LoginResposta(BaseModel):
    id: int
    nome: str


app = FastAPI()


@app.post("/registro", response_model=RegistroResposta, status_code=status.HTTP_201_CREATED)
def registro(usuario_in: UsuarioRegistro, db: Session = Depends(get_db)):
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario_in.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ja cadastrado."
        )

    novo_usuario = Usuario(
        email=usuario_in.email,
        senha=hash_password(usuario_in.senha),
        nome=usuario_in.nome
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return {"id": novo_usuario.id}


@app.post("/login", response_model=LoginResposta, status_code=status.HTTP_200_OK)
def login(credenciais: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == credenciais.email).first()
    dummy_hash = "00000000000000000000000000000000:0000000000000000000000000000000000000000000000000000000000000000"

    if not usuario:
        verify_password(credenciais.senha, dummy_hash)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas."
        )

    if not verify_password(credenciais.senha, usuario.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas."
        )

    return {"id": usuario.id, "nome": usuario.nome}