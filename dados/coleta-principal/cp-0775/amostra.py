from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

app = FastAPI()


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    db_path = os.environ.get("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definida")
    return create_engine(f"sqlite:///{db_path}", future=True)


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    sql = """
        SELECT id, nome, categoria, preco, estoque
        FROM produtos
        WHERE 1=1
    """
    params: dict[str, object] = {}

    if nome is not None:
        sql += " AND nome LIKE :nome"
        params["nome"] = f"%{nome}%"
    if categoria is not None:
        sql += " AND categoria = :categoria"
        params["categoria"] = categoria
    if preco_min is not None:
        sql += " AND preco >= :preco_min"
        params["preco_min"] = preco_min
    if preco_max is not None:
        sql += " AND preco <= :preco_max"
        params["preco_max"] = preco_max

    if ordenar_por == "preco":
        sql += " ORDER BY preco ASC"
    elif ordenar_por == "nome":
        sql += " ORDER BY nome ASC"

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [ProdutoOut(**row) for row in rows]