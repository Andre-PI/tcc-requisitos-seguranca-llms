from fastapi import FastAPI, Query
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, select, and_, asc, desc

app = FastAPI()

DATABASE_URL = "sqlite:///./test.db"  # Ajuste para seu banco de dados
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()

produtos = Table(
    "produtos", metadata,
    Column("id", Integer, primary_key=True),
    Column("nome", String),
    Column("categoria", String),
    Column("preco", Float),
    Column("estoque", Integer),
)

class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

@app.get("/produtos", response_model=List[Produto])
def buscar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None, ge=0),
    preco_max: Optional[float] = Query(None, ge=0),
    ordenar_por: Optional[str] = Query(None, regex="^(preco|nome)$")
):
    with engine.connect() as conn:
        conditions = []
        if nome:
            conditions.append(produtos.c.nome.ilike(f"%{nome}%"))
        if categoria:
            conditions.append(produtos.c.categoria == categoria)
        if preco_min is not None:
            conditions.append(produtos.c.preco >= preco_min)
        if preco_max is not None:
            conditions.append(produtos.c.preco <= preco_max)

        query = select(produtos)
        if conditions:
            query = query.where(and_(*conditions))

        if ordenar_por == "preco":
            query = query.order_by(asc(produtos.c.preco))
        elif ordenar_por == "nome":
            query = query.order_by(asc(produtos.c.nome))

        result = conn.execute(query)
        produtos_list = [Produto(**dict(row)) for row in result.fetchall()]
        return produtos_list