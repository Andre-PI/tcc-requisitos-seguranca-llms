import os
from typing import Generator
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session, Mapped, mapped_column

DB_PATH = os.environ.get("TCC_DB_PATH", "database.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    senha: Mapped[str] = mapped_column(nullable=False)
    nome: Mapped[str] = mapped_column(nullable=False)

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

@app.post("/registro", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def registro(usuario_data: RegistroRequest, db: Session = Depends(get_db)):
    novo_usuario = Usuario(
        email=usuario_data.email,
        senha=usuario_data.senha,
        nome=usuario_data.nome,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return {"id": novo_usuario.id}

@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    stmt = select(Usuario).where(
        Usuario.email == login_data.email,
        Usuario.senha == login_data.senha
    )
    usuario = db.execute(stmt).scalars().first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas"
        )
        
    return {"id": usuario.id, "nome": usuario.nome}