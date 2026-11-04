import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_url = f"sqlite:///{db_path}"
else:
    db_url = db_path

engine = create_engine(db_url, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    senha: Mapped[str] = mapped_column(nullable=False)
    nome: Mapped[str] = mapped_column(nullable=False)


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


@app.post("/registro", status_code=status.HTTP_201_CREATED, response_model=RegistroResponse)
def registro(dados: RegistroRequest):
    with Session(engine) as session:
        usuario_existente = session.scalar(select(Usuario).where(Usuario.email == dados.email))
        if usuario_existente:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")

        novo_usuario = Usuario(email=dados.email, senha=dados.senha, nome=dados.nome)
        session.add(novo_usuario)
        session.commit()
        session.refresh(novo_usuario)
        return {"id": novo_usuario.id}


@app.post("/login", status_code=status.HTTP_200_OK, response_model=LoginResponse)
def login(dados: LoginRequest):
    with Session(engine) as session:
        usuario = session.scalar(
            select(Usuario).where(Usuario.email == dados.email, Usuario.senha == dados.senha)
        )
        if not usuario:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        return {"id": usuario.id, "nome": usuario.nome}