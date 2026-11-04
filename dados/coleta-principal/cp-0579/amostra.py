from __future__ import annotations

import os
from typing import Any, Optional, Literal

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

app = FastAPI(title="Produtos API")

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("A variável de ambiente TCC_DB_PATH deve estar definida antes da importação.")

if DB_PATH.startswith("sqlite:///") or DB_PATH.startswith("sqlite://"):
    DATABASE_URL = DB_PATH
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)


@app.get("/produtos")
def listar_produtos(
    nome: Optional[str] = Query(default=None, description="Busca parcial por nome"),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
) -> list[dict[str, Any]]:
    query = "SELECT id, nome, categoria, preco, estoque FROM produtos"
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
        query += " WHERE " + " AND ".join(conditions)

    if ordenar_por == "preco":
        query += " ORDER BY preco ASC"
    elif ordenar_por == "nome":
        query += " ORDER BY nome ASC"

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = result.mappings().all()

    return [dict(row) for row in rows]