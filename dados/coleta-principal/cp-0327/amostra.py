import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, select, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_url = f"sqlite:///{db_path}"
else:
    db_url = db_path

engine = create_engine(db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProdutoModel(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    categoria = Column(String)
    preco = Column(Float)
    estoque = Column(Integer)


class ProdutoSchema(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    class Config:
        from_attributes = True


app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/produtos", response_model=List[ProdutoSchema])
def listar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(ProdutoModel)

    if nome is not None:
        query = query.where(ProdutoModel.nome.contains(nome))
    if categoria is not None:
        query = query.where(ProdutoModel.categoria == categoria)
    if preco_min is not None:
        query = query.where(ProdutoModel.preco >= preco_min)
    if preco_max is not None:
        query = query.where(ProdutoModel.preco <= preco_max)

    if ordenar_por == "preco":
        query = query.order_by(ProdutoModel.preco.asc())
    elif ordenar_por == "nome":
        query = query.order_by(ProdutoModel.nome.asc())

    produtos = db.scalars(query).all()
    return produtos