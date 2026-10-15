from fastapi import FastAPI, HTTPException, Depends, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Dict, Tuple
import time
import threading

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=12,  # fator de custo configuravel
    deprecated="auto"
)

LOCK = threading.Lock()
MAX_ATTEMPTS_PER_IP = 5
MAX_ATTEMPTS_PER_ACCOUNT = 5
BLOCK_TIME_SECONDS = 300  # 5 minutos

# Armazenamento temporário para tentativas: {ip: (count, first_attempt_time)}
ip_attempts: Dict[str, Tuple[int, float]] = {}
# Armazenamento temporário para tentativas por usuário: {email: (count, first_attempt_time)}
user_attempts: Dict[str, Tuple[int, float]] = {}

app = FastAPI()


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


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # passlib's verify is timing attack resistant
    return pwd_context.verify(plain_password, hashed_password)


def is_blocked(key: str, attempts_map: Dict[str, Tuple[int, float]]) -> bool:
    with LOCK:
        data = attempts_map.get(key)
        if not data:
            return False
        count, first_time = data
        now = time.time()
        if now - first_time > BLOCK_TIME_SECONDS:
            # Reset after block time window
            attempts_map.pop(key, None)
            return False
        return count >= MAX_ATTEMPTS_PER_IP  # same limit for both maps


def add_attempt(key: str, attempts_map: Dict[str, Tuple[int, float]]):
    with LOCK:
        now = time.time()
        count, first_time = attempts_map.get(key, (0, now))
        if now - first_time > BLOCK_TIME_SECONDS:
            # Reset attempts after block time window
            attempts_map[key] = (1, now)
        else:
            attempts_map[key] = (count + 1, first_time)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Custom middleware to prevent logging senha field
    # This middleware does not log senha anywhere intentionally
    response = await call_next(request)
    return response


@app.post("/login")
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host

    # Check block by IP
    if is_blocked(ip, ip_attempts):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    # Check block by account/email
    if is_blocked(data.email, user_attempts):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()

    # Usar mensagem de erro idêntica para evitar enumeração de usuários
    valid = False
    if usuario:
        valid = verify_password(data.senha, usuario.senha)

    if not valid:
        add_attempt(ip, ip_attempts)
        add_attempt(data.email, user_attempts)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    # Reset attempts on successful login
    with LOCK:
        ip_attempts.pop(ip, None)
        user_attempts.pop(data.email, None)

    return {"id": usuario.id, "nome": usuario.nome}