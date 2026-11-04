import os
import time
import hmac
import hashlib
import secrets
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, select, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH", "usuarios.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

PBKDF2_ITERATIONS = 600000

def hash_senha(senha: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"

def verificar_senha(senha_fornecida: str, hash_armazenado: str) -> bool:
    try:
        parts = hash_armazenado.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        hash_esperado = bytes.fromhex(parts[3])
        novo_hash = hashlib.pbkdf2_hmac("sha256", senha_fornecida.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(hash_esperado, novo_hash)
    except Exception:
        return False

DUMMY_SALT = secrets.token_bytes(16)
DUMMY_HASH = f"pbkdf2_sha256${PBKDF2_ITERATIONS}${DUMMY_SALT.hex()}${hashlib.pbkdf2_hmac('sha256', b'dummy', DUMMY_SALT, PBKDF2_ITERATIONS).hex()}"

attempts_ip = defaultdict(list)
attempts_email = defaultdict(list)

MAX_ATTEMPTS = 5
LOCKOUT_TIME = 300

def checar_rate_limit(chave: str, registros: dict) -> bool:
    agora = time.time()
    limite = agora - LOCKOUT_TIME
    registros[chave] = [t for t in registros[chave] if t > limite]
    return len(registros[chave]) >= MAX_ATTEMPTS

def registrar_tentativa(chave: str, registros: dict):
    registros[chave].append(time.time())

def resetar_tentativas(chave: str, registros: dict):
    if chave in registros:
        del registros[chave]

class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

app = FastAPI()

@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(dados: RegistroRequest):
    email_normalizado = dados.email.lower()
    with SessionLocal() as db:
        usuario_existente = db.execute(
            select(Usuario).where(Usuario.email == email_normalizado)
        ).scalar_one_or_none()
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ja cadastrado"
            )

        hash_gerado = hash_senha(dados.senha)
        novo_usuario = Usuario(
            email=email_normalizado,
            senha=hash_gerado,
            nome=dados.nome
        )
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        return {"id": novo_usuario.id}

@app.post("/login")
def login(dados: LoginRequest, request: Request):
    ip_cliente = request.client.host if request.client else "127.0.0.1"
    email_normalizado = dados.email.lower()

    if checar_rate_limit(ip_cliente, attempts_ip) or checar_rate_limit(email_normalizado, attempts_email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde."
        )

    with SessionLocal() as db:
        usuario = db.execute(
            select(Usuario).where(Usuario.email == email_normalizado)
        ).scalar_one_or_none()

        hash_para_verificar = usuario.senha if usuario else DUMMY_HASH
        valido = verificar_senha(dados.senha, hash_para_verificar)

        if not usuario or not valido:
            registrar_tentativa(ip_cliente, attempts_ip)
            registrar_tentativa(email_normalizado, attempts_email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas"
            )

        resetar_tentativas(ip_cliente, attempts_ip)
        resetar_tentativas(email_normalizado, attempts_email)

        return {"id": usuario.id, "nome": usuario.nome}