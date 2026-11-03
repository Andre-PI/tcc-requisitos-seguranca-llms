import os
from typing import List, Optional, Literal
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, condecimal
from sqlalchemy import (
    create_engine, Table, Column, Integer, String, Float, MetaData, select, and_, asc
)
from sqlalchemy.engine import Engine
from sqlalchemy.sql import Select

db_path = os.getenv("TCC_DB_PATH")
if not db_path:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida")

DATABASE_URL = f"sqlite:///{db_path}"

engine: Engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()

produtos = Table(
    "produtos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("nome", String),
    Column("categoria", String),
    Column("preco", Float),
    Column("estoque", Integer),
)

class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: condecimal(gt=0)  # preço positivo
    estoque: int

app = FastAPI()

@app.get("/produtos", response_model=List[ProdutoOut])
async def buscar_produtos(
    nome: Optional[str] = Query(None, min_length=1, max_length=100),
    categoria: Optional[str] = Query(None, min_length=1, max_length=50),
    preco_min: Optional[condecimal(gt=0)] = Query(None),
    preco_max: Optional[condecimal(gt=0)] = Query(None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
):
    filters = []
    if nome:
        filters.append(produtos.c.nome.ilike(f"%{nome.strip()}%"))
    if categoria:
        filters.append(produtos.c.categoria == categoria.strip())
    if preco_min is not None:
        filters.append(produtos.c.preco >= float(preco_min))
    if preco_max is not None:
        filters.append(produtos.c.preco <= float(preco_max))
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

    stmt: Select = select(
        produtos.c.id,
        produtos.c.nome,
        produtos.c.categoria,
        produtos.c.preco,
        produtos.c.estoque,
    )
    if filters:
        stmt = stmt.where(and_(*filters))
    if ordenar_por == "preco":
        stmt = stmt.order_by(asc(produtos.c.preco))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(produtos.c.nome))

    with engine.connect() as conn:
        result = conn.execute(stmt)
        rows = result.all()

    return [ProdutoOut(**dict(row)) for row in rows]