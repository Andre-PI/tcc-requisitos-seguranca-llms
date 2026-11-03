import os
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, constr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy import Integer, String, Column
import hashlib
import hmac

DB_PATH = os.environ["TCC_DB_PATH"]
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    nome = Column(String, nullable=False)

app = FastAPI()

class RegistroRequest(BaseModel):
    email: EmailStr
    senha: constr(min_length=8)
    nome: constr(min_length=1)

class RegistroResponse(BaseModel):
    id: int

class LoginRequest(BaseModel):
    email: EmailStr
    senha: constr(min_length=8)

class LoginResponse(BaseModel):
    id: int
    nome: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    # Use SHA-256 with a fixed salt for demonstration; in prod use stronger hash + unique salt per user
    salt = b"TCC_SALT_V1"
    pwd_bytes = password.encode("utf-8")
    return hashlib.sha256(salt + pwd_bytes).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(hash_password(plain_password), hashed_password)

@app.post("/registro", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def registro(data: RegistroRequest, db: Session = Depends(get_db)):
    hashed = hash_password(data.senha)
    novo_usuario = Usuario(email=data.email, senha=hashed, nome=data.nome)
    db.add(novo_usuario)
    try:
        db.commit()
        db.refresh(novo_usuario)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado.")
    return RegistroResponse(id=novo_usuario.id)

@app.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    stmt = select(Usuario).where(Usuario.email == data.email)
    usuario = db.execute(stmt).scalar_one_or_none()
    if not usuario or not verify_password(data.senha, usuario.senha):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    return LoginResponse(id=usuario.id, nome=usuario.nome)