import os
from decimal import Decimal
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, and_, asc, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

if DB_PATH.startswith("sqlite:///"):
    DATABASE_URL = DB_PATH
elif DB_PATH.startswith("/"):
    DATABASE_URL = f"sqlite:///{DB_PATH}"
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
)

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

app = FastAPI()


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


@app.get("/produtos", response_model=list[ProdutoOut], status_code=200)
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None, min_length=1, max_length=200)] = None,
    categoria: Annotated[Optional[str], Query(default=None, min_length=1, max_length=100)] = None,
    preco_min: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    preco_max: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    ordenar_por: Annotated[Optional[Literal["preco", "nome"]], Query(default=None)] = None,
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

    conditions = []

    if nome is not None:
        conditions.append(produtos.c.nome.ilike(f"%{nome}%"))
    if categoria is not None:
        conditions.append(produtos.c.categoria == categoria)
    if preco_min is not None:
        conditions.append(produtos.c.preco >= preco_min)
    if preco_max is not None:
        conditions.append(produtos.c.preco <= preco_max)

    stmt = select(
        produtos.c.id,
        produtos.c.nome,
        produtos.c.categoria,
        produtos.c.preco,
        produtos.c.estoque,
    )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    if ordenar_por == "preco":
        stmt = stmt.order_by(asc(produtos.c.preco), asc(produtos.c.id))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(produtos.c.nome), asc(produtos.c.id))
    else:
        stmt = stmt.order_by(asc(produtos.c.id))

    try:
        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar produtos")

    result = []
    for row in rows:
        result.append(
            {
                "id": int(row["id"]),
                "nome": row["nome"],
                "categoria": row["categoria"],
                "preco": float(row["preco"]) if row["preco"] is not None else 0.0,
                "estoque": int(row["estoque"]),
            }
        )

    return result