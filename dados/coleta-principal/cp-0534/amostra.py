import os
from typing import Annotated, Optional

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)


@app.get("/produtos")
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None)] = None,
    categoria: Annotated[Optional[str], Query(default=None)] = None,
    preco_min: Annotated[Optional[float], Query(default=None)] = None,
    preco_max: Annotated[Optional[float], Query(default=None)] = None,
    ordenar_por: Annotated[Optional[str], Query(default=None, pattern="^(preco|nome)$")] = None,
):
    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    where = []
    params = {}

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
        sql += " WHERE " + " AND ".join(where)

    if ordenar_por == "preco":
        sql += " ORDER BY preco ASC"
    elif ordenar_por == "nome":
        sql += " ORDER BY nome ASC"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(row) for row in rows]