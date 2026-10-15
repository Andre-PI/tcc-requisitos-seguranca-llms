from fastapi import FastAPI, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from collections import defaultdict
import time
import asyncio

DATABASE_URL = "sqlite:///./test.db"  # Ajuste conforme necessário

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)  # custo configurável

app = FastAPI()

# Limites
MAX_ATTEMPTS_PER_IP = 5
MAX_ATTEMPTS_PER_USER = 5
BLOCK_TIME_SECONDS = 300  # 5 minutos

# Estruturas para controle de tentativas
login_attempts_ip = defaultdict(lambda: {"count": 0, "first_attempt": 0})
login_attempts_user = defaultdict(lambda: {"count": 0, "first_attempt": 0})

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_blocked(key: str, attempts_dict: dict) -> bool:
    data = attempts_dict[key]
    now = time.time()
    if data["count"] >= MAX_ATTEMPTS_PER_IP and now - data["first_attempt"] < BLOCK_TIME_SECONDS:
        return True
    elif now - data["first_attempt"] >= BLOCK_TIME_SECONDS:
        # Resetar contador após bloqueio expirar
        attempts_dict[key] = {"count": 0, "first_attempt": 0}
        return False
    return False

def register_attempt(key: str, attempts_dict: dict):
    now = time.time()
    data = attempts_dict[key]
    if data["first_attempt"] == 0 or now - data["first_attempt"] > BLOCK_TIME_SECONDS:
        attempts_dict[key] = {"count": 1, "first_attempt": now}
    else:
        data["count"] += 1

@app.post("/login")
async def login(request: Request, login: LoginRequest, db: Session = Depends(get_db)):
    ip = request.client.host

    if is_blocked(ip, login_attempts_ip):
        # Bloqueio por IP
        await asyncio.sleep(0.5)  # Delay para dificultar brute force
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    if is_blocked(login.email, login_attempts_user):
        # Bloqueio por usuário
        await asyncio.sleep(0.5)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    user = db.query(Usuario).filter(Usuario.email == login.email).first()

    # Verificação segura de senha, mesmo se usuário não existir
    valid = False
    hashed = user.senha if user else pwd_context.hash("fakepassword")
    try:
        valid = pwd_context.verify(login.senha, hashed)
    except Exception:
        valid = False

    if not user or not valid:
        register_attempt(ip, login_attempts_ip)
        register_attempt(login.email, login_attempts_user)
        await asyncio.sleep(0.5)  # Delay para dificultar brute force
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    # Login bem-sucedido: resetar contadores
    if ip in login_attempts_ip:
        login_attempts_ip.pop(ip)
    if login.email in login_attempts_user:
        login_attempts_user.pop(login.email)

    return {"id": user.id, "nome": user.nome}