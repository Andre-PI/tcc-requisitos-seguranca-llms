import hashlib
import hmac
import os
import secrets
from typing import Generator
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, select, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_path = f"sqlite:///{db_path}"

engine = create_engine(db_path, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 600_000
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    return f"{salt}${iterations}${hash_bytes.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        salt, iterations_str, hash_hex = stored_hash.split("$")
        iterations = int(iterations_str)
        hash_bytes = bytes.fromhex(hash_hex)
        candidate_bytes = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations
        )
        return hmac.compare_digest(candidate_bytes, hash_bytes)
    except Exception:
        return False


# Dummy hash para mitigar timing attacks quando o usuário não existir
DUMMY_HASH = hash_password("dummy_password_for_timing_mitigation")

app = FastAPI()


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


@app.post(
    "/registro",
    response_model=RegistroResponse,
    status_code=status.HTTP_201_CREATED,
)
def registro(dados: RegistroRequest, db: Session = Depends(get_db)):
    usuario_existente = db.execute(
        select(Usuario).where(Usuario.email == dados.email)
    ).scalar_one_or_none()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado",
        )

    novo_usuario = Usuario(
        email=dados.email,
        senha=hash_password(dados.senha),
        nome=dados.nome,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return RegistroResponse(id=novo_usuario.id)


@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.execute(
        select(Usuario).where(Usuario.email == dados.email)
    ).scalar_one_or_none()

    if usuario is None:
        verify_password(dados.senha, DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    if not verify_password(dados.senha, usuario.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    return LoginResponse(id=usuario.id, nome=usuario.nome)