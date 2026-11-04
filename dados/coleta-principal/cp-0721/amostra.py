from __future__ import annotations

import os
from decimal import Decimal
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import MetaData, Table, asc, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("A variável de ambiente TCC_DB_PATH deve estar definida antes da importação.")

DATABASE_URL = f"sqlite+pysqlite:///{DB_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},
)

metadata = MetaData()

produtos = Table(
    "produtos",
    metadata,
    autoload_with=engine,
)

app = FastAPI(title="API de Produtos")


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


@app.get("/produtos", response_model=list[ProdutoOut], response_model_exclude_none=True)
def listar_produtos(
    nome: str | None = Query(default=None, min_length=1, max_length=200),
    categoria: str | None = Query(default=None, min_length=1, max_length=200),
    preco_min: float | None = Query(default=None, ge=0),
    preco_max: float | None = Query(default=None, ge=0),
    ordenar_por: Literal["preco", "nome"] | None = Query(default=None),
) -> list[dict[str, Any]]:
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max.")

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
        stmt = stmt.where(*conditions)

    if ordenar_por == "preco":
        stmt = stmt.order_by(asc(produtos.c.preco), asc(produtos.c.nome), asc(produtos.c.id))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(produtos.c.nome), asc(produtos.c.id))

    try:
        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Erro ao consultar produtos.") from exc

    return [
        {
            "id": row["id"],
            "nome": row["nome"],
            "categoria": row["categoria"],
            "preco": float(row["preco"]) if isinstance(row["preco"], Decimal) else row["preco"],
            "estoque": row["estoque"],
        }
        for row in rows
    ]