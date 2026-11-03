import os
from fastapi import FastAPI, Query
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import create_engine, Table, Column, Integer, String, Float, MetaData, select, and_, asc
from sqlalchemy.orm import Session

db_path = os.environ["TCC_DB_PATH"]
engine = create_engine(f"sqlite:///{db_path}", future=True)
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

app = FastAPI()

@app.get("/produtos", response_model=List[Produto])
def buscar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[str] = Query(None, regex="^(preco|nome)$")
):
    with Session(engine) as session:
        query = select(produtos)
        filtros = []
        if nome:
            filtros.append(produtos.c.nome.ilike(f"%{nome}%"))
        if categoria:
            filtros.append(produtos.c.categoria == categoria)
        if preco_min is not None:
            filtros.append(produtos.c.preco >= preco_min)
        if preco_max is not None:
            filtros.append(produtos.c.preco <= preco_max)
        if filtros:
            query = query.where(and_(*filtros))
        if ordenar_por == "preco":
            query = query.order_by(asc(produtos.c.preco))
        elif ordenar_por == "nome":
            query = query.order_by(asc(produtos.c.nome))
        results = session.execute(query).all()
        return [Produto(**dict(row._mapping)) for row in results]