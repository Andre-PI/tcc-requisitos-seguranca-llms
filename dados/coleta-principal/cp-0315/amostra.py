from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

app = FastAPI(title="Produtos API")

_DB_PATH = os.getenv("TCC_DB_PATH")
if not _DB_PATH:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida.")

_DATABASE_URL = f"sqlite:///{_DB_PATH}"
engine: Engine = create_engine(_DATABASE_URL, future=True)


@app.get("/produtos")
def listar_produtos(
    nome: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    preco_min: float | None = Query(default=None),
    preco_max: float | None = Query(default=None),
    ordenar_por: str | None = Query(default=None, pattern="^(preco|nome)$"),
) -> list[dict[str, Any]]:
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

    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    if ordenar_por == "preco":
        sql += " ORDER BY preco ASC"
    elif ordenar_por == "nome":
        sql += " ORDER BY nome ASC"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    result: list[dict[str, Any]] = []
    for row in rows:
        preco = row["preco"]
        if isinstance(preco, Decimal):
            preco = float(preco)
        result.append(
            {
                "id": row["id"],
                "nome": row["nome"],
                "categoria": row["categoria"],
                "preco": preco,
                "estoque": row["estoque"],
            }
        )

    return result