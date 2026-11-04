from __future__ import annotations

import os
from decimal import Decimal
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, MetaData, Numeric, String, Table, asc, create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},
)

metadata = MetaData()

produtos = Table(
    "produtos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("nome", String),
    Column("categoria", String),
    Column("preco", Numeric),
    Column("estoque", Integer),
)

app = FastAPI()


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


@app.get("/produtos", response_model=list[ProdutoOut], response_model_exclude_none=True)
def listar_produtos(
    nome: Annotated[Optional[str], Query(min_length=1, max_length=200)] = None,
    categoria: Annotated[Optional[str], Query(min_length=1, max_length=100)] = None,
    preco_min: Annotated[Optional[float], Query(ge=0)] = None,
    preco_max: Annotated[Optional[float], Query(ge=0)] = None,
    ordenar_por: Annotated[Optional[Literal["preco", "nome"]], Query()] = None,
):
    try:
        stmt = select(
            produtos.c.id,
            produtos.c.nome,
            produtos.c.categoria,
            produtos.c.preco,
            produtos.c.estoque,
        )

        conditions = []

        if nome is not None:
            nome_clean = nome.strip()
            if nome_clean:
                conditions.append(produtos.c.nome.ilike(f"%{nome_clean}%"))

        if categoria is not None:
            categoria_clean = categoria.strip()
            if categoria_clean:
                conditions.append(produtos.c.categoria == categoria_clean)

        if preco_min is not None:
            conditions.append(produtos.c.preco >= Decimal(str(preco_min)))

        if preco_max is not None:
            conditions.append(produtos.c.preco <= Decimal(str(preco_max)))

        if conditions:
            stmt = stmt.where(*conditions)

        if ordenar_por == "preco":
            stmt = stmt.order_by(asc(produtos.c.preco), asc(produtos.c.id))
        elif ordenar_por == "nome":
            stmt = stmt.order_by(asc(produtos.c.nome), asc(produtos.c.id))
        else:
            stmt = stmt.order_by(asc(produtos.c.id))

        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()

        result = []
        for row in rows:
            result.append(
                {
                    "id": row["id"],
                    "nome": row["nome"],
                    "categoria": row["categoria"],
                    "preco": float(row["preco"]) if row["preco"] is not None else None,
                    "estoque": row["estoque"],
                }
            )

        return JSONResponse(content=result, status_code=200)
    except SQLAlchemyError:
        return JSONResponse(content={"detail": "Erro ao consultar produtos."}, status_code=500)