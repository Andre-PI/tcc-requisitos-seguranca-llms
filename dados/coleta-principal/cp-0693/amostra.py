import os
import time
import secrets
import hashlib
import hmac
from collections import defaultdict
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, select, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Configuração de hash de senhas (PBKDF2-HMAC-SHA256 padrão da biblioteca padrão)
PBKDF2_ITERATIONS = 100_000

# Armazenamento em memória para Rate Limiting
# Janela de 60 segundos, limite de 5 tentativas falhas por IP e por e-mail
RATE_LIMIT_WINDOW = 60
MAX_ATTEMPTS = 5
failed_attempts_by_ip: Dict[str, List[float]] = defaultdict(list)
failed_attempts_by_email: Dict[str, List[float]] = defaultdict(list)

# Hash dummy pré-computado para mitigar timing attack em caso de e-mail não encontrado
DUMMY_SALT = secrets.token_hex(16)
DUMMY_HASH = hashlib.pbkdf2_hmac(
    "sha256", "dummy_password".encode("utf-8"), DUMMY_SALT.encode("utf-8"), PBKDF2_ITERATIONS
).hex()
DUMMY_PASSWORD_RECORD = f"{PBKDF2_ITERATIONS}${DUMMY_SALT}${DUMMY_HASH}"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    )
    return f"{PBKDF2_ITERATIONS}${salt}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        iterations_str, salt, original_hash = stored_hash.split("$")
        iterations = int(iterations_str)
        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
        )
        return hmac.compare_digest(key.hex(), original_hash)
    except Exception:
        return False


def is_rate_limited(key: str, tracker: Dict[str, List[float]]) -> bool:
    now = time.time()
    # Remove tentativas expiradas
    tracker[key] = [t for t in tracker[key] if now - t < RATE_LIMIT_WINDOW]
    return len(tracker[key]) >= MAX_ATTEMPTS


def record_failed_attempt(key: str, tracker: Dict[str, List[float]]) -> None:
    now = time.time()
    tracker[key] = [t for t in tracker[key] if now - t < RATE_LIMIT_WINDOW]
    tracker[key].append(now)


# Configuração do Banco de Dados
db_path = os.getenv("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite"):
    db_url = f"sqlite:///{db_path}"
else:
    db_url = db_path

engine = create_engine(db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)


# Esquemas Pydantic
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
    with SessionLocal() as session:
        usuario_existente = session.scalar(
            select(Usuario).where(Usuario.email == dados.email.lower())
        )
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-mail ja cadastrado."
            )

        hashed_password = hash_password(dados.senha)
        novo_usuario = Usuario(
            email=dados.email.lower(),
            senha=hashed_password,
            nome=dados.nome
        )
        session.add(novo_usuario)
        session.commit()
        session.refresh(novo_usuario)

        return {"id": novo_usuario.id}


@app.post("/login", status_code=status.HTTP_200_OK, response_model=LoginResponse)
def login(dados: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    email_key = dados.email.lower()

    if is_rate_limited(client_ip, failed_attempts_by_ip) or is_rate_limited(email_key, failed_attempts_by_email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde."
        )

    with SessionLocal() as session:
        usuario = session.scalar(select(Usuario).where(Usuario.email == email_key))

        # Mitigação de timing attack: se o usuário não existe, verifica contra hash dummy
        password_to_check = usuario.senha if usuario else DUMMY_PASSWORD_RECORD
        senha_valida = verify_password(dados.senha, password_to_check)

        if not usuario or not senha_valida:
            record_failed_attempt(client_ip, failed_attempts_by_ip)
            record_failed_attempt(email_key, failed_attempts_by_email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas."
            )

        # Sucesso: limpa tentativas falhas do usuário
        failed_attempts_by_email.pop(email_key, None)

        return {"id": usuario.id, "nome": usuario.nome}