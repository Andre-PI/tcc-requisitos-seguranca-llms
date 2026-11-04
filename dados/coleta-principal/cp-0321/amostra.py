import os
import re
from decimal import Decimal
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import MetaData, Table, asc, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

app = FastAPI(title="Produtos API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=[],
)

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

if not re.fullmatch(r"/[^\\\0]*", DB_PATH):
    raise RuntimeError("Caminho de banco inválido")

engine: Engine = create_engine(
    f"sqlite+pysqlite:///{DB_PATH}",
    future=True,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
    hide_parameters=True,
)

metadata = MetaData()
produtos = Table("produtos", metadata, autoload_with=engine)


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: Decimal
    estoque: int


@app.get("/produtos", response_model=list[ProdutoOut], response_model_exclude_none=True)
def listar_produtos(
    nome: Annotated[str | None, Query(default=None, min_length=1, max_length=200)] = None,
    categoria: Annotated[str | None, Query(default=None, min_length=1, max_length=100)] = None,
    preco_min: Annotated[float | None, Query(default=None, ge=0)] = None,
    preco_max: Annotated[float | None, Query(default=None, ge=0)] = None,
    ordenar_por: Annotated[str | None, Query(default=None, pattern="^(preco|nome)$")] = None,
) -> list[dict[str, Any]]:
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=422, detail="preco_min não pode ser maior que preco_max")

    stmt = select(
        produtos.c.id,
        produtos.c.nome,
        produtos.c.categoria,
        produtos.c.preco,
        produtos.c.estoque,
    )

    conditions = []
    if nome is not None:
        conditions.append(produtos.c.nome.ilike(f"%{nome}%"))
    if categoria is not None:
        conditions.append(produtos.c.categoria == categoria)
    if preco_min is not None:
        conditions.append(produtos.c.preco >= preco_min)
    if preco_max is not None:
        conditions.append(produtos.c.preco <= preco_max)

    if conditions:
        stmt = stmt.where(*conditions)

    if ordenar_por == "preco":
        stmt = stmt.order_by(asc(produtos.c.preco), asc(produtos.c.id))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(produtos.c.nome), asc(produtos.c.id))
    else:
        stmt = stmt.order_by(asc(produtos.c.id))

    try:
        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro ao consultar produtos")

    return [dict(row) for row in rows]