import os
from typing import List, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Float, Integer, String, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite://"):
    db_url = f"sqlite:///{db_path}"
else:
    db_url = db_path

engine = create_engine(db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProdutoDB(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    categoria = Column(String)
    preco = Column(Float)
    estoque = Column(Integer)


class ProdutoResponse(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    model_config = ConfigDict(from_attributes=True)


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoResponse])
def get_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[str] = Query(None, pattern="^(preco|nome)$"),
):
    with SessionLocal() as session:
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

        results = session.execute(query).scalars().all()
        return results