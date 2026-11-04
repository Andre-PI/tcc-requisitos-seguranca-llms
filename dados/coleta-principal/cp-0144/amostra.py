from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text

app = FastAPI()


def _get_db_url() -> str:
    db_path = os.environ.get("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definida")
    return f"sqlite+pysqlite:///{db_path}"


engine = create_engine(_get_db_url(), future=True)


@app.get("/produtos")
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[str] = Query(default=None, pattern="^(preco|nome)$"),
) -> list[dict[str, Any]]:
    sql = [
        "SELECT id, nome, categoria, preco, estoque",
        "FROM produtos",
    ]
    where = []
    params: dict[str, Any] = {}

    if nome is not None:
        where.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"
    if categoria is not None:
        where.append("categoria = :categoria")
        params["categoria"] = categoria
    if preco_min is not None:
        where.append("preco >= :preco_min")
        params["preco_min"] = preco_min
    if preco_max is not None:
        where.append("preco <= :preco_max")
        params["preco_max"] = preco_max

    if where:
        sql.append("WHERE " + " AND ".join(where))

    if ordenar_por == "preco":
        sql.append("ORDER BY preco ASC")
    elif ordenar_por == "nome":
        sql.append("ORDER BY nome ASC")

    query = " ".join(sql)

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()

    return [dict(row) for row in rows]