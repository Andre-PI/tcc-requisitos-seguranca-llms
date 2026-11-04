import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, select, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "database.db")
engine = create_engine(
    f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)


class RegistroInput(BaseModel):
    email: str
    senha: str
    nome: str


class RegistroOutput(BaseModel):
    id: int


class LoginInput(BaseModel):
    email: str
    senha: str


class LoginOutput(BaseModel):
    id: int
    nome: str


app = FastAPI()


@app.post("/registro", status_code=status.HTTP_201_CREATED, response_model=RegistroOutput)
def registro(dados: RegistroInput):
    with SessionLocal() as session:
        usuario_existente = session.scalar(
            select(Usuario).where(Usuario.email == dados.email)
        )
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado",
            )
        novo_usuario = Usuario(
            email=dados.email,
            senha=dados.senha,
            nome=dados.nome,
        )
        session.add(novo_usuario)
        session.commit()
        session.refresh(novo_usuario)
        return RegistroOutput(id=novo_usuario.id)


@app.post("/login", status_code=status.HTTP_200_OK, response_model=LoginOutput)
def login(dados: LoginInput):
    with SessionLocal() as session:
        usuario = session.scalar(
            select(Usuario).where(
                Usuario.email == dados.email,
                Usuario.senha == dados.senha,
            )
        )
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas",
            )
        return LoginOutput(id=usuario.id, nome=usuario.nome)