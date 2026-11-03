import os
from typing import Any, Optional

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.environ.get("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definido")
    return db_path


def _get_engine() -> Engine:
    db_path = _get_db_path()
    return create_engine(f"sqlite:///{db_path}", future=True)


engine = _get_engine()


@app.get("/produtos")
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[str] = Query(default=None, pattern="^(preco|nome)$"),
) -> list[dict[str, Any]]:
    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    filtros = []
    params: dict[str, Any] = {}

    if nome is not None:
        filtros.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"
    if categoria is not None:
        filtros.append("categoria = :categoria")
        params["categoria"] = categoria
    if preco_min is not None:
        filtros.append("preco >= :preco_min")
        params["preco_min"] = preco_min
    if preco_max is not None:
        filtros.append("preco <= :preco_max")
        params["preco_max"] = preco_max

    if filtros:
        sql += " WHERE " + " AND ".join(filtros)

    if ordenar_por == "preco":
        sql += " ORDER BY preco ASC"
    elif ordenar_por == "nome":
        sql += " ORDER BY nome ASC"

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.mappings().all()

    return [dict(row) for row in rows]