from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, MetaData, Table, select, and_, asc
from sqlalchemy.engine import Engine

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida")
    return db_path


def _get_engine() -> Engine:
    db_path = _get_db_path()
    return create_engine(f"sqlite:///{db_path}", future=True)


engine = _get_engine()
metadata = MetaData()
produtos = Table("produtos", metadata, autoload_with=engine)


@app.get("/produtos")
def listar_produtos(
    nome: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    preco_min: float | None = Query(default=None),
    preco_max: float | None = Query(default=None),
    ordenar_por: str | None = Query(default=None, pattern="^(preco|nome)$"),
) -> list[dict[str, Any]]:
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
        stmt = stmt.order_by(asc(produtos.c.preco))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(produtos.c.nome))

    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    return [dict(row) for row in rows]