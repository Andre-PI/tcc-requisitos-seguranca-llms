from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine: Engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

app = FastAPI()


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


class ProdutoQuery(BaseModel):
    nome: str | None = None
    categoria: str | None = None
    preco_min: float | None = Field(default=None, ge=0)
    preco_max: float | None = Field(default=None, ge=0)
    ordenar_por: Literal["preco", "nome"] = "nome"

    @field_validator("nome", "categoria")
    @classmethod
    def validar_texto(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("preco_max")
    @classmethod
    def validar_preco_max(cls, v: float | None, info: Any) -> float | None:
        if v is None:
            return v
        preco_min = info.data.get("preco_min")
        if preco_min is not None and v < preco_min:
            raise ValueError("preco_max deve ser maior ou igual a preco_min")
        return v


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    preco_min: float | None = Query(default=None, ge=0),
    preco_max: float | None = Query(default=None, ge=0),
    ordenar_por: Literal["preco", "nome"] = Query(default="nome"),
):
    try:
        q = ProdutoQuery(
            nome=nome,
            categoria=categoria,
            preco_min=preco_min,
            preco_max=preco_max,
            ordenar_por=ordenar_por,
        )
    except Exception:
        raise HTTPException(status_code=422, detail="Parâmetros inválidos")

    where_clauses: list[str] = []
    params: dict[str, Any] = {}

    if q.nome is not None:
        where_clauses.append("nome LIKE :nome")
        params["nome"] = f"%{q.nome}%"
    if q.categoria is not None:
        where_clauses.append("categoria = :categoria")
        params["categoria"] = q.categoria
    if q.preco_min is not None:
        where_clauses.append("preco >= :preco_min")
        params["preco_min"] = q.preco_min
    if q.preco_max is not None:
        where_clauses.append("preco <= :preco_max")
        params["preco_max"] = q.preco_max

    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    order_map = {
        "preco": "preco ASC",
        "nome": "nome ASC",
    }
    sql += f" ORDER BY {order_map[q.ordenar_por]}"

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params)
            rows = result.mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar produtos")

    return [ProdutoOut(**row) for row in rows]