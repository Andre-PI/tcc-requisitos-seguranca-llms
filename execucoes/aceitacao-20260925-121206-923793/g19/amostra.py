from fastapi import FastAPI, Query, HTTPException
from typing import Optional, List, Literal
from pydantic import BaseModel, condecimal
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Numeric, select, and_, asc
from sqlalchemy.sql import text
from sqlalchemy.engine import Result

app = FastAPI()

DATABASE_URL = "sqlite:///./test.db"  # Ajuste para seu banco de dados real

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()

produtos = Table(
    "produtos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("nome", String, nullable=False),
    Column("categoria", String, nullable=False),
    Column("preco", Numeric(10, 2), nullable=False),
    Column("estoque", Integer, nullable=False),
)

class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: condecimal(max_digits=10, decimal_places=2)
    estoque: int

@app.get("/produtos", response_model=List[ProdutoOut])
def buscar_produtos(
    nome: Optional[str] = Query(None, min_length=1, max_length=100),
    categoria: Optional[str] = Query(None, min_length=1, max_length=50),
    preco_min: Optional[condecimal(gt=0, max_digits=10, decimal_places=2)] = None,
    preco_max: Optional[condecimal(gt=0, max_digits=10, decimal_places=2)] = None,
    ordenar_por: Optional[Literal["preco", "nome"]] = None,
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

    conditions = []
    if nome:
        conditions.append(produtos.c.nome.ilike(f"%{nome.strip()}%"))
    if categoria:
        conditions.append(produtos.c.categoria == categoria.strip())
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

    with engine.connect() as conn:
        result: Result = conn.execute(query)
        rows = result.fetchall()

    return [ProdutoOut(**dict(row)) for row in rows]