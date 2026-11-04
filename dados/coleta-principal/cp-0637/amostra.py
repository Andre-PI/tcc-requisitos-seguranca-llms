import hashlib
import hmac
import os
import secrets
from typing import Generator
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, select, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_path = f"sqlite:///{db_path}"

engine = create_engine(
    db_path,
    connect_args={"check_same_thread": False} if "sqlite" in db_path else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    kdf_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 600000)
    return f"{salt}:{kdf_hash.hex()}"


def verify_password(stored_password: str, provided_password: str) -> bool:
    try:
        salt, expected_hash = stored_password.split(":")
        calc_hash = hashlib.pbkdf2_hmac("sha256", provided_password.encode("utf-8"), salt.encode("utf-8"), 600000)
        return hmac.compare_digest(expected_hash, calc_hash.hex())
    except Exception:
        return False


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


@app.post("/registro", status_code=status.HTTP_201_CREATED, response_model=RegistroResponse)
def registro(dados: RegistroRequest, db: Session = Depends(get_db)):
    stmt = select(Usuario).where(Usuario.email == dados.email)
    usuario_existente = db.execute(stmt).scalar_one_or_none()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ja cadastrado."
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


@app.post("/login", status_code=status.HTTP_200_OK, response_model=LoginResponse)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    stmt = select(Usuario).where(Usuario.email == dados.email)
    usuario = db.execute(stmt).scalar_one_or_none()

    dummy_salt = "00000000000000000000000000000000"
    dummy_hash = hashlib.pbkdf2_hmac("sha256", b"dummy", dummy_salt.encode("utf-8"), 600000).hex()
    dummy_stored = f"{dummy_salt}:{dummy_hash}"

    if usuario is None:
        verify_password(dummy_stored, dados.senha)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas."
        )

    if not verify_password(usuario.senha, dados.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas."
        )

    return {"id": usuario.id, "nome": usuario.nome}