from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, asc, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("A variável de ambiente TCC_DB_PATH deve estar definida antes da importação.")

DATABASE_URL = f"sqlite:///{DB_PATH}"

metadata = MetaData()

produtos_table = Table(
    "produtos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("nome", String, nullable=False),
    Column("categoria", String, nullable=False),
    Column("preco", Float, nullable=False),
    Column("estoque", Integer, nullable=False),
)


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


engine: Engine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = create_engine(
        DATABASE_URL,
        future=True,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )
    try:
        yield
    finally:
        if engine is not None:
            engine.dispose()
            engine = None


app = FastAPI(lifespan=lifespan)


@app.get("/produtos", response_model=list[ProdutoOut], status_code=200)
def listar_produtos(
    nome: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    categoria: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    preco_min: Annotated[float | None, Query(ge=0)] = None,
    preco_max: Annotated[float | None, Query(ge=0)] = None,
    ordenar_por: Annotated[Literal["preco", "nome"] | None, Query()] = None,
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max.")

    if engine is None:
        raise HTTPException(status_code=500, detail="Banco de dados indisponível.")

    stmt = select(
        produtos_table.c.id,
        produtos_table.c.nome,
        produtos_table.c.categoria,
        produtos_table.c.preco,
        produtos_table.c.estoque,
    )

    conditions = []
    if nome is not None:
        conditions.append(produtos_table.c.nome.ilike(f"%{nome}%"))
    if categoria is not None:
        conditions.append(produtos_table.c.categoria == categoria)
    if preco_min is not None:
        conditions.append(produtos_table.c.preco >= preco_min)
    if preco_max is not None:
        conditions.append(produtos_table.c.preco <= preco_max)

    if conditions:
        stmt = stmt.where(*conditions)

    if ordenar_por == "preco":
        stmt = stmt.order_by(asc(produtos_table.c.preco), asc(produtos_table.c.nome), asc(produtos_table.c.id))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(produtos_table.c.nome), asc(produtos_table.c.id))
    else:
        stmt = stmt.order_by(asc(produtos_table.c.id))

    try:
        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro ao consultar o banco de dados.")

    return [ProdutoOut.model_validate(row) for row in rows]