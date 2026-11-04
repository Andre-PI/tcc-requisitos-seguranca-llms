from __future__ import annotations

import os
from decimal import Decimal
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, MetaData, Numeric, String, Table, and_, asc, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite+pysqlite:///{DB_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

metadata = MetaData()

produtos = Table(
    "produtos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("nome", String, nullable=False),
    Column("categoria", String, nullable=False),
    Column("preco", Numeric, nullable=False),
    Column("estoque", Integer, nullable=False),
)

app = FastAPI(title="Busca de Produtos")


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


@app.get("/produtos", response_model=list[ProdutoOut], response_model_exclude_none=True)
def listar_produtos(
    nome: str | None = Query(default=None, min_length=1, max_length=200),
    categoria: str | None = Query(default=None, min_length=1, max_length=200),
    preco_min: float | None = Query(default=None, ge=0),
    preco_max: float | None = Query(default=None, ge=0),
    ordenar_por: Literal["preco", "nome"] | None = Query(default=None),
) -> Any:
    try:
        filtros = []

        if nome is not None:
            filtros.append(produtos.c.nome.ilike(f"%{nome}%"))
        if categoria is not None:
            filtros.append(produtos.c.categoria == categoria)
        if preco_min is not None:
            filtros.append(produtos.c.preco >= Decimal(str(preco_min)))
        if preco_max is not None:
            filtros.append(produtos.c.preco <= Decimal(str(preco_max)))

        if preco_min is not None and preco_max is not None and preco_min > preco_max:
            raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

        stmt = select(
            produtos.c.id,
            produtos.c.nome,
            produtos.c.categoria,
            produtos.c.preco,
            produtos.c.estoque,
        )

        if filtros:
            stmt = stmt.where(and_(*filtros))

        if ordenar_por == "preco":
            stmt = stmt.order_by(asc(produtos.c.preco), asc(produtos.c.id))
        elif ordenar_por == "nome":
            stmt = stmt.order_by(asc(produtos.c.nome), asc(produtos.c.id))
        else:
            stmt = stmt.order_by(asc(produtos.c.id))

        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()

        resultado = []
        for row in rows:
            resultado.append(
                {
                    "id": row["id"],
                    "nome": row["nome"],
                    "categoria": row["categoria"],
                    "preco": float(row["preco"]) if row["preco"] is not None else None,
                    "estoque": row["estoque"],
                }
            )

        return JSONResponse(status_code=200, content=resultado)

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro ao consultar produtos")
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno do servidor")