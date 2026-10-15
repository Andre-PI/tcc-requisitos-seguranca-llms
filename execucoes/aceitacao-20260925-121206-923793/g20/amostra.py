from typing import List, Optional, Literal
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, condecimal, validator
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Numeric, select, and_, asc, desc
from sqlalchemy.sql import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

# Configuração da conexão com o banco de dados (exemplo SQLite)
DATABASE_URL = "sqlite:///./test.db"
engine: Engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

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

# Modelo Pydantic para resposta
class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: condecimal(max_digits=10, decimal_places=2)
    estoque: int

@app.get("/produtos", response_model=List[Produto])
async def buscar_produtos(
    nome: Optional[str] = Query(None, min_length=1, max_length=100),
    categoria: Optional[str] = Query(None, min_length=1, max_length=50),
    preco_min: Optional[condecimal(gt=0, max_digits=10, decimal_places=2)] = None,
    preco_max: Optional[condecimal(gt=0, max_digits=10, decimal_places=2)] = None,
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

    query = select([
        produtos.c.id,
        produtos.c.nome,
        produtos.c.categoria,
        produtos.c.preco,
        produtos.c.estoque
    ])

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

    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            produtos_list = [Produto(**dict(row)) for row in result.fetchall()]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar produtos")

    return produtos_list