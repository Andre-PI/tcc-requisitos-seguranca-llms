from typing import Generator, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from passlib.context import CryptContext

DATABASE_URL = "sqlite:///./app.db"

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = __import__("sqlalchemy").Column(__import__("sqlalchemy").Integer, primary_key=True, index=True)
    email = __import__("sqlalchemy").Column(__import__("sqlalchemy").String(255), unique=True, index=True, nullable=False)
    senha = __import__("sqlalchemy").Column(__import__("sqlalchemy").String(255), nullable=False)
    nome = __import__("sqlalchemy").Column(__import__("sqlalchemy").String(255), nullable=False)


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    id: int
    nome: str


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        stmt = select(Usuario).where(Usuario.email == payload.email)
        usuario: Optional[Usuario] = db.execute(stmt).scalars().first()
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    if not usuario or not verify_password(payload.senha, usuario.senha):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return LoginResponse(id=usuario.id, nome=usuario.nome)