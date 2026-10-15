from fastapi import FastAPI, HTTPException, Depends, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import threading

# Configurações do banco (exemplo SQLite, ajuste conforme necessário)
DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# Modelo SQLAlchemy
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

# Configuração do hash de senha
pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=12,  # fator de custo configurável
    deprecated="auto"
)

# Pydantic schema
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

class LoginResponse(BaseModel):
    id: int
    nome: str

app = FastAPI()

# Limites de tentativas
MAX_ATTEMPTS_PER_IP = 10
MAX_ATTEMPTS_PER_USER = 5
LOCK_TIME_SECONDS = 300  # 5 minutos bloqueio

# Estruturas para controle de tentativas
attempts_ip = {}
attempts_user = {}
lock_ip = {}
lock_user = {}

lock = threading.Lock()

def clean_expired_locks():
    now = time.time()
    with lock:
        for ip in list(lock_ip.keys()):
            if lock_ip[ip] < now:
                del lock_ip[ip]
        for user in list(lock_user.keys()):
            if lock_user[user] < now:
                del lock_user[user]

def increase_attempts(ip: str, user: str):
    now = time.time()
    with lock:
        # Limpa locks expirados antes
        clean_expired_locks()

        attempts_ip[ip] = attempts_ip.get(ip, 0) + 1
        attempts_user[user] = attempts_user.get(user, 0) + 1

        if attempts_ip[ip] >= MAX_ATTEMPTS_PER_IP:
            lock_ip[ip] = now + LOCK_TIME_SECONDS
            attempts_ip[ip] = 0  # reset após bloqueio

        if attempts_user[user] >= MAX_ATTEMPTS_PER_USER:
            lock_user[user] = now + LOCK_TIME_SECONDS
            attempts_user[user] = 0

def is_locked(ip: str, user: str) -> bool:
    now = time.time()
    with lock:
        clean_expired_locks()
        if ip in lock_ip and lock_ip[ip] > now:
            return True
        if user in lock_user and lock_user[user] > now:
            return True
    return False

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Comparação resistente a temporização já garantida pelo passlib
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/login", response_model=LoginResponse)
async def login(login_req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host
    user_key = login_req.email.lower()

    if is_locked(ip, user_key):
        # Mensagem padronizada para não dar pistas
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    stmt = select(Usuario).where(Usuario.email == user_key)
    usuario = db.execute(stmt).scalars().first()

    # Faz verificação "dummy" para evitar timing attack e enumeração
    fake_hash = pwd_context.hash("fake_password_to_compare")
    hashed = usuario.senha if usuario else fake_hash

    password_valid = verify_password(login_req.senha, hashed)

    if not (usuario and password_valid):
        increase_attempts(ip, user_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    # Reset attempts on successful login
    with lock:
        attempts_ip.pop(ip, None)
        attempts_user.pop(user_key, None)

    return LoginResponse(id=usuario.id, nome=usuario.nome)