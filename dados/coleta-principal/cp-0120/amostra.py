import os
import hashlib
import hmac
from typing import Generator
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

db_path = os.environ.get("TCC_DB_PATH", "usuarios.db")
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)

def hash_senha(senha: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{key.hex()}"

def verificar_senha(senha_fornecida: str, senha_armazenada: str) -> bool:
    try:
        salt_hex, key_hex = senha_armazenada.split(":")
        salt = bytes.fromhex(salt_hex)
        key_esperada = bytes.fromhex(key_hex)
        chave_calculada = hashlib.pbkdf2_hmac("sha256", senha_fornecida.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(chave_calculada, key_esperada)
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

@app.post("/registro", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def registro(dados: RegistroRequest, db: Session = Depends(get_db)):
    usuario_existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ja cadastrado."
        )

    novo_usuario = Usuario(
        email=dados.email,
        senha=hash_senha(dados.senha),
        nome=dados.nome
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return {"id": novo_usuario.id}

@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if not usuario or not verificar_senha(dados.senha, usuario.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas."
        )

    return {"id": usuario.id, "nome": usuario.nome}