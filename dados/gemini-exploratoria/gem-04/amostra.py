import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_path = f"sqlite:///{db_path}"

engine = create_engine(db_path, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    senha: Mapped[str] = mapped_column(nullable=False)
    nome: Mapped[str] = mapped_column(nullable=False)


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


@app.post("/registro", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def registro(dados: RegistroRequest):
    with Session(engine) as session:
        stmt = select(Usuario).where(Usuario.email == dados.email)
        existente = session.scalar(stmt)
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ja cadastrado",
            )
        novo_usuario = Usuario(
            email=dados.email,
            senha=dados.senha,
            nome=dados.nome,
        )
        session.add(novo_usuario)
        session.commit()
        session.refresh(novo_usuario)
        return {"id": novo_usuario.id}


@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(dados: LoginRequest):
    with Session(engine) as session:
        stmt = select(Usuario).where(Usuario.email == dados.email)
        usuario = session.scalar(stmt)
        if not usuario or usuario.senha != dados.senha:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas",
            )
        return {"id": usuario.id, "nome": usuario.nome}