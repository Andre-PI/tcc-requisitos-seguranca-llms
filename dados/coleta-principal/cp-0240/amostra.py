from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine: Engine = create_engine(
    f"sqlite+pysqlite:///{DB_PATH}",
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},
)

app = FastAPI(title="Produtos")


class ProdutoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value if value else None


@app.get("/produtos", response_model=list[ProdutoOut], status_code=200)
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None, min_length=1, max_length=200)] = None,
    categoria: Annotated[Optional[str], Query(default=None, min_length=1, max_length=100)] = None,
    preco_min: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    preco_max: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    ordenar_por: Annotated[Optional[Literal["preco", "nome"]], Query(default=None)] = None,
) -> list[ProdutoOut]:
    nome = _normalize_text(nome)
    categoria = _normalize_text(categoria)

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
    else:
        sql += " ORDER BY id ASC"

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.mappings().all()

    produtos: list[ProdutoOut] = []
    for row in rows:
        produtos.append(
            ProdutoOut(
                id=int(row["id"]),
                nome=str(row["nome"]),
                categoria=str(row["categoria"]),
                preco=float(row["preco"]),
                estoque=int(row["estoque"]),
            )
        )

    return produtos