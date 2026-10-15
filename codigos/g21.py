from fastapi import FastAPI, Query, HTTPException
from typing import List, Optional, Literal
from pydantic import BaseModel, condecimal, validator
from sqlalchemy import create_engine, MetaData, Table, select, and_, or_, asc, desc
from sqlalchemy.sql import text
from sqlalchemy.engine import Result
import decimal

app = FastAPI()

DATABASE_URL = "sqlite:///./test.db"  # Substitua pela sua string de conexão real
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()
produtos = Table(
    "produtos",
    metadata,
    autoload_with=engine
)

class ProdutoResponse(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: condecimal(max_digits=10, decimal_places=2)
    estoque: int

@app.get("/produtos", response_model=List[ProdutoResponse])
def buscar_produtos(
    nome: Optional[str] = Query(None, min_length=1, max_length=100),
    categoria: Optional[str] = Query(None, min_length=1, max_length=50),
    preco_min: Optional[condecimal(gt=0, max_digits=10, decimal_places=2)] = None,
    preco_max: Optional[condecimal(gt=0, max_digits=10, decimal_places=2)] = None,
    ordenar_por: Optional[Literal["preco", "nome"]] = None
):
    conditions = []

    if nome:
        # Busca parcial segura com ilike
        conditions.append(produtos.c.nome.ilike(f"%{nome}%"))
    if categoria:
        conditions.append(produtos.c.categoria == categoria)
    if preco_min is not None:
        conditions.append(produtos.c.preco >= preco_min)
    if preco_max is not None:
        conditions.append(produtos.c.preco <= preco_max)
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

    query = select(produtos)
    if conditions:
        query = query.where(and_(*conditions))
    if ordenar_por:
        order_column = produtos.c.preco if ordenar_por == "preco" else produtos.c.nome
        query = query.order_by(asc(order_column))

    with engine.connect() as conn:
        result: Result = conn.execute(query)
        rows = result.fetchall()

    return [ProdutoResponse(**dict(row)) for row in rows]