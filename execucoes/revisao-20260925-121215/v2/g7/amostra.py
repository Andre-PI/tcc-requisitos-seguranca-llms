from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from passlib.context import CryptContext

DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # Ajuste para seu banco de dados
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False)  # senha hash armazenada
    nome = Column(String, nullable=False)


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class LoginResponse(BaseModel):
    id: int
    nome: str


async def get_user_by_email(db: AsyncSession, email: str) -> Usuario | None:
    result = await db.execute(select(Usuario).where(Usuario.email == email))
    return result.scalars().first()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@app.post("/login", response_model=LoginResponse, status_code=200)
async def login(login_req: LoginRequest, db: AsyncSession = Depends(async_session)):
    user = await get_user_by_email(db, login_req.email)
    if not user or not verify_password(login_req.senha, user.senha):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return LoginResponse(id=user.id, nome=user.nome)