from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import FastAPI, Query
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, and_, create_engine, select
from sqlalchemy.engine import Engine

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("A variável de ambiente TCC_DB_PATH deve estar definida antes da importação.")

db_url = f"sqlite:///{DB_PATH}"
engine: Engine = create_engine(db_url, future=True)

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


@app.get("/produtos")
def listar_produtos(
    nome: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    preco_min: float | None = Query(default=None),
    preco_max: float | None = Query(default=None),
    ordenar_por: Literal["preco", "nome"] | None = Query(default=None),
) -> list[dict[str, Any]]:
    conditions = []

    if nome is not None and nome != "":
        conditions.append(produtos.c.nome.ilike(f"%{nome}%"))
    if categoria is not None and categoria != "":
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
        stmt = stmt.order_by(produtos.c.preco.asc())
    elif ordenar_por == "nome":
        stmt = stmt.order_by(produtos.c.nome.asc())

    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    return [dict(row) for row in rows]