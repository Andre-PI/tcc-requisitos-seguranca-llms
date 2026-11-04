import os
from typing import Generator
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session

db_path = os.environ.get("TCC_DB_PATH", "database.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)


app = FastAPI()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


@app.post("/registro", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def registro(dados: RegistroRequest, db: Session = Depends(get_db)):
    usuario = Usuario(email=dados.email, senha=dados.senha, nome=dados.nome)
    db.add(usuario)
    try:
        db.commit()
        db.refresh(usuario)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Erro ao registrar usuário.")
    return {"id": usuario.id}


@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    stmt = select(Usuario).where(Usuario.email == dados.email)
    usuario = db.execute(stmt).scalar_one_or_none()

    if not usuario or usuario.senha != dados.senha:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
        )

    return {"id": usuario.id, "nome": usuario.nome}