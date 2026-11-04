import os
from typing import Generator
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session

db_path = os.environ.get("TCC_DB_PATH", "database.db")
engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)


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


app = FastAPI()


@app.post("/registro", status_code=status.HTTP_201_CREATED, response_model=RegistroResponse)
def registro(dados: RegistroRequest, db: Session = Depends(get_db)):
    usuario = Usuario(email=dados.email, senha=dados.senha, nome=dados.nome)
    db.add(usuario)
    try:
        db.commit()
        db.refresh(usuario)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao cadastrar usuário."
        )
    return {"id": usuario.id}


@app.post("/login", status_code=status.HTTP_200_OK, response_model=LoginResponse)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    stmt = select(Usuario).where(Usuario.email == dados.email, Usuario.senha == dados.senha)
    usuario = db.execute(stmt).scalar_one_or_none()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas"
        )
    return {"id": usuario.id, "nome": usuario.nome}