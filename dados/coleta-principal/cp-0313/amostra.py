from __future__ import annotations

import os
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

if DB_PATH.startswith("sqlite:///") or DB_PATH.startswith("sqlite://"):
    DATABASE_URL = DB_PATH
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

app = FastAPI(title="Produtos API", version="1.0.0")


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: Decimal = Field(..., description="Preço do produto")
    estoque: int


@app.get("/produtos", response_model=list[ProdutoOut], status_code=200)
def listar_produtos(
    nome: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    categoria: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    preco_min: Annotated[float | None, Query(ge=0)] = None,
    preco_max: Annotated[float | None, Query(ge=0)] = None,
    ordenar_por: Annotated[Literal["preco", "nome"] | None, Query()] = None,
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

    where_clauses: list[str] = []
    params: dict[str, object] = {}

    if nome is not None:
        where_clauses.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"

    if categoria is not None:
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
        sql += " ORDER BY preco ASC, id ASC"
    elif ordenar_por == "nome":
        sql += " ORDER BY nome ASC, id ASC"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [
        ProdutoOut(
            id=row["id"],
            nome=row["nome"],
            categoria=row["categoria"],
            preco=row["preco"],
            estoque=row["estoque"],
        )
        for row in rows
    ]