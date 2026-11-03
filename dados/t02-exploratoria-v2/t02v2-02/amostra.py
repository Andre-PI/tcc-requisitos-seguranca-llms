import os
from fastapi import FastAPI, Query
from typing import Optional, List, Literal
from pydantic import BaseModel
from sqlalchemy import create_engine, Table, Column, Integer, String, Float, MetaData, select, and_, asc
from sqlalchemy.engine import Engine

db_path = os.getenv("TCC_DB_PATH")
engine: Engine = create_engine(f"sqlite:///{db_path}", future=True)
metadata = MetaData()

produtos = Table(
    "produtos", metadata,
    Column("id", Integer, primary_key=True),
    Column("nome", String),
    Column("categoria", String),
    Column("preco", Float),
    Column("estoque", Integer),
)

app = FastAPI()

class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

@app.get("/produtos", response_model=List[Produto])
async def busca_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
):
    conditions = []
    if nome is not None:
        conditions.append(produtos.c.nome.ilike(f"%{nome}%"))
    if categoria is not None:
        conditions.append(produtos.c.categoria == categoria)
    if preco_min is not None:
        conditions.append(produtos.c.preco >= preco_min)
    if preco_max is not None:
        conditions.append(produtos.c.preco <= preco_max)

    stmt = select(produtos)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    if ordenar_por == "preco":
        stmt = stmt.order_by(asc(produtos.c.preco))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(produtos.c.nome))

    with engine.connect() as conn:
        result = conn.execute(stmt)
        rows = result.fetchall()

    return [Produto(id=r.id, nome=r.nome, categoria=r.categoria, preco=r.preco, estoque=r.estoque) for r in rows]