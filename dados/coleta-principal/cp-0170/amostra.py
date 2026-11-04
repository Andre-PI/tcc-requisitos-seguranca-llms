from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

app = FastAPI()

_DB_PATH = os.getenv("TCC_DB_PATH")
if not _DB_PATH:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida.")

_engine: Engine = create_engine(f"sqlite:///{_DB_PATH}", future=True)


@app.get("/produtos")
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[str] = Query(default=None, pattern="^(preco|nome)$"),
) -> list[dict[str, Any]]:
    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    conditions: list[str] = []
    params: dict[str, Any] = {}

    if nome is not None:
        conditions.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"
    if categoria is not None:
        conditions.append("categoria = :categoria")
        params["categoria"] = categoria
    if preco_min is not None:
        conditions.append("preco >= :preco_min")
        params["preco_min"] = preco_min
    if preco_max is not None:
        conditions.append("preco <= :preco_max")
        params["preco_max"] = preco_max

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    if ordenar_por == "preco":
        sql += " ORDER BY preco ASC"
    elif ordenar_por == "nome":
        sql += " ORDER BY nome ASC"

    with _engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(row) for row in rows]