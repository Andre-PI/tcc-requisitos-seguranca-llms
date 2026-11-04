from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import FastAPI, Query
from sqlalchemy import Column, Float, Integer, String, Table, and_, asc, create_engine, MetaData, select
from sqlalchemy.engine import Engine

app = FastAPI()

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("A variável de ambiente TCC_DB_PATH deve estar definida antes da importação.")

engine: Engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
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
    nome: str | None = Query(default=None, description="Busca parcial no nome"),
    categoria: str | None = Query(default=None),
    preco_min: float | None = Query(default=None),
    preco_max: float | None = Query(default=None),
    ordenar_por: Literal["preco", "nome"] | None = Query(default=None),
) -> list[dict[str, Any]]:
    stmt = select(
        produtos.c.id,
        produtos.c.nome,
        produtos.c.categoria,
        produtos.c.preco,
        produtos.c.estoque,
    )

    filtros = []
    if nome is not None:
        filtros.append(produtos.c.nome.ilike(f"%{nome}%"))
    if categoria is not None:
        filtros.append(produtos.c.categoria == categoria)
    if preco_min is not None:
        filtros.append(produtos.c.preco >= preco_min)
    if preco_max is not None:
        filtros.append(produtos.c.preco <= preco_max)

    if filtros:
        stmt = stmt.where(and_(*filtros))

    if ordenar_por == "preco":
        stmt = stmt.order_by(asc(produtos.c.preco))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(produtos.c.nome))

    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    return [dict(row) for row in rows]