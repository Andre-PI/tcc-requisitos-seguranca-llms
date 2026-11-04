from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definido")
    return db_path


def _get_engine() -> Engine:
    return create_engine(f"sqlite:///{_get_db_path()}", future=True)


@app.get("/produtos")
def listar_produtos(
    nome: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    preco_min: float | None = Query(default=None),
    preco_max: float | None = Query(default=None),
    ordenar_por: str | None = Query(default=None, pattern="^(preco|nome)$"),
) -> list[dict[str, Any]]:
    engine = _get_engine()

    sql = [
        "SELECT id, nome, categoria, preco, estoque",
        "FROM produtos",
    ]
    where_clauses: list[str] = []
    params: dict[str, Any] = {}

    if nome is not None and nome != "":
        where_clauses.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"
    if categoria is not None and categoria != "":
        where_clauses.append("categoria = :categoria")
        params["categoria"] = categoria
    if preco_min is not None:
        where_clauses.append("preco >= :preco_min")
        params["preco_min"] = preco_min
    if preco_max is not None:
        where_clauses.append("preco <= :preco_max")
        params["preco_max"] = preco_max

    if where_clauses:
        sql.append("WHERE " + " AND ".join(where_clauses))

    if ordenar_por == "preco":
        sql.append("ORDER BY preco ASC")
    elif ordenar_por == "nome":
        sql.append("ORDER BY nome ASC")

    query = text("\n".join(sql))

    with engine.connect() as conn:
        rows = conn.execute(query, params).mappings().all()

    return [dict(row) for row in rows]