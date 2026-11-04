import os
import re
from decimal import Decimal
from typing import Annotated, Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

if DB_PATH.startswith("sqlite:///"):
    DATABASE_URL = DB_PATH
elif DB_PATH.startswith("sqlite:"):
    DATABASE_URL = DB_PATH
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

app = FastAPI(title="Produtos API", version="1.0.0")

_engine: Engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},
)

_IDENTIFIER_SAFE = re.compile(r"^[A-Za-z0-9_]+$")


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    nome: str
    categoria: str
    preco: Decimal
    estoque: int


@app.get("/produtos", response_model=list[ProdutoOut], response_model_exclude_none=True)
def listar_produtos(
    nome: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    categoria: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    preco_min: Annotated[float | None, Query(ge=0)] = None,
    preco_max: Annotated[float | None, Query(ge=0)] = None,
    ordenar_por: Annotated[str | None, Query(pattern="^(preco|nome)$")] = None,
):
    where_clauses: list[str] = []
    params: dict[str, Any] = {}

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

    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        return JSONResponse(status_code=200, content=[])

    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    order_column = "id"
    if ordenar_por == "preco":
        order_column = "preco"
    elif ordenar_por == "nome":
        order_column = "nome"

    if not _IDENTIFIER_SAFE.match(order_column):
        order_column = "id"

    sql += f" ORDER BY {order_column} ASC"

    with _engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.mappings().all()

    return [ProdutoOut.model_validate(row) for row in rows]