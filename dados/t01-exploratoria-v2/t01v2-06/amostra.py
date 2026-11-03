import os
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

DATABASE_URL = f"sqlite:///{os.environ['TCC_DB_PATH']}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()

usuarios = Table(
    "usuarios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, unique=True, nullable=False),
    Column("senha", String, nullable=False),
    Column("nome", String, nullable=False),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

app = FastAPI()

class RegistroSchema(BaseModel):
    email: str
    senha: str
    nome: str

class LoginSchema(BaseModel):
    email: str
    senha: str

class RegistroResponseSchema(BaseModel):
    id: int

class LoginResponseSchema(BaseModel):
    id: int
    nome: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/registro", status_code=201, response_model=RegistroResponseSchema)
def registro(usuario: RegistroSchema, db=Depends(get_db)):
    ins = usuarios.insert().values(email=usuario.email, senha=usuario.senha, nome=usuario.nome)
    try:
        result = db.execute(ins)
        db.commit()
        return {"id": result.inserted_primary_key[0]}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")

@app.post("/login", response_model=LoginResponseSchema)
def login(credenciais: LoginSchema, db=Depends(get_db)):
    stmt = select(usuarios.c.id, usuarios.c.nome).where(
        usuarios.c.email == credenciais.email,
        usuarios.c.senha == credenciais.senha
    )
    result = db.execute(stmt).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    return {"id": result.id, "nome": result.nome}