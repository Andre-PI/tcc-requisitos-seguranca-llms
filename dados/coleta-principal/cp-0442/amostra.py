import os
import hashlib
import hmac
from typing import Generator
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, String, Integer
from sqlalchemy.orm import declarative_base, mapped_column, Mapped, sessionmaker, Session

db_path = os.environ.get("TCC_DB_PATH", "test.db")
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    senha: Mapped[str] = mapped_column(String, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
    return f"{salt.hex()}${pwd_hash.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        computed_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 600000)
        return hmac.compare_digest(computed_hash, expected_hash)
    except (ValueError, AttributeError):
        return False


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


@app.post("/registro", status_code=status.HTTP_201_CREATED, response_model=RegistroResponse)
def registro(dados: RegistroRequest, db: Session = Depends(get_db)):
    usuario_existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ja cadastrado"
        )

    novo_usuario = Usuario(
        email=dados.email,
        senha=hash_password(dados.senha),
        nome=dados.nome
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return RegistroResponse(id=novo_usuario.id)


@app.post("/login", status_code=status.HTTP_200_OK, response_model=LoginResponse)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()

    dummy_hash = "00" * 16 + "$" + "00" * 32
    senha_valida = verify_password(dados.senha, usuario.senha if usuario else dummy_hash)

    if not usuario or not senha_valida:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas"
        )

    return LoginResponse(id=usuario.id, nome=usuario.nome)