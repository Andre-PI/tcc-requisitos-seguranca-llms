import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, select, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session

db_path = os.environ.get("TCC_DB_PATH", "")
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProdutoDB(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True)
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
    query = select(ProdutoDB)

    if nome:
        query = query.where(ProdutoDB.nome.contains(nome))
    if categoria:
        query = query.where(ProdutoDB.categoria == categoria)
    if preco_min is not None:
        query = query.where(ProdutoDB.preco >= preco_min)
    if preco_max is not None:
        query = query.where(ProdutoDB.preco <= preco_max)

    if ordenar_por == "preco":
        query = query.order_by(ProdutoDB.preco.asc())
    elif ordenar_por == "nome":
        query = query.order_by(ProdutoDB.nome.asc())

    resultados = db.execute(query).scalars().all()
    return resultados