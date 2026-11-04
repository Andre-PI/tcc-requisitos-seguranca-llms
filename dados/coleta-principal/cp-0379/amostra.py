from __future__ import annotations

import os
from decimal import Decimal
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, and_, asc, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida.")

if DB_PATH.startswith("sqlite:///") or DB_PATH.startswith("sqlite:////"):
    DATABASE_URL = DB_PATH
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    future=True,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
)

metadata = MetaData()

produtos = Table(
    "produtos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("nome", String, nullable=False),
    Column("categoria", String, nullable=False),
    Column("preco", Float, nullable=False),
    Column("estoque", Integer, nullable=False),
)

app = FastAPI(title="Produtos API", version="1.0.0")


class ProdutoOut(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: int = Field(ge=1)
    nome: str = Field(min_length=1, max_length=255)
    categoria: str = Field(min_length=1, max_length=255)
    preco: float
    estoque: int


@app.get("/produtos", response_model=list[ProdutoOut], response_model_exclude_none=True)
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None, min_length=1, max_length=255)] = None,
    categoria: Annotated[Optional[str], Query(default=None, min_length=1, max_length=255)] = None,
    preco_min: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    preco_max: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    ordenar_por: Annotated[Optional[Literal["preco", "nome"]], Query(default=None)] = None,
):
    try:
        conditions = []

        if nome is not None:
            conditions.append(produtos.c.nome.ilike(f"%{nome}%"))
        if categoria is not None:
            conditions.append(produtos.c.categoria == categoria)
        if preco_min is not None:
            conditions.append(produtos.c.preco >= preco_min)
        if preco_max is not None:
            conditions.append(produtos.c.preco <= preco_max)

        stmt = select(
            produtos.c.id,
            produtos.c.nome,
            produtos.c.categoria,
            produtos.c.preco,
            produtos.c.estoque,
        )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        if ordenar_por == "preco":
            stmt = stmt.order_by(asc(produtos.c.preco), asc(produtos.c.id))
        elif ordenar_por == "nome":
            stmt = stmt.order_by(asc(produtos.c.nome), asc(produtos.c.id))
        else:
            stmt = stmt.order_by(asc(produtos.c.id))

        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()

        result = [
            {
                "id": int(row["id"]),
                "nome": str(row["nome"]),
                "categoria": str(row["categoria"]),
                "preco": float(Decimal(str(row["preco"]))),
                "estoque": int(row["estoque"]),
            }
            for row in rows
        ]
        return JSONResponse(content=result, status_code=200)
    except SQLAlchemyError:
        return JSONResponse(content={"detail": "Erro interno ao consultar produtos."}, status_code=500)