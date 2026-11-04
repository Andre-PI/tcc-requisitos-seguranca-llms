from __future__ import annotations

import os
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, Query
from sqlalchemy import MetaData, Table, asc, create_engine, select
from sqlalchemy.engine import Engine

app = FastAPI()

_db_path = os.environ.get("TCC_DB_PATH")
if not _db_path:
    raise RuntimeError("A variável de ambiente TCC_DB_PATH deve estar definida antes da importação.")

_engine: Engine = create_engine(f"sqlite:///{_db_path}", future=True)
_metadata = MetaData()

_produtos = Table("produtos", _metadata, autoload_with=_engine)


@app.get("/produtos")
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None)] = None,
    categoria: Annotated[Optional[str], Query(default=None)] = None,
    preco_min: Annotated[Optional[float], Query(default=None)] = None,
    preco_max: Annotated[Optional[float], Query(default=None)] = None,
    ordenar_por: Annotated[Optional[Literal["preco", "nome"]], Query(default=None)] = None,
):
    stmt = select(
        _produtos.c.id,
        _produtos.c.nome,
        _produtos.c.categoria,
        _produtos.c.preco,
        _produtos.c.estoque,
    )

    conditions = []
    if nome is not None:
        conditions.append(_produtos.c.nome.ilike(f"%{nome}%"))
    if categoria is not None:
        conditions.append(_produtos.c.categoria == categoria)
    if preco_min is not None:
        conditions.append(_produtos.c.preco >= preco_min)
    if preco_max is not None:
        conditions.append(_produtos.c.preco <= preco_max)

    if conditions:
        stmt = stmt.where(*conditions)

    if ordenar_por == "preco":
        stmt = stmt.order_by(asc(_produtos.c.preco))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(_produtos.c.nome))

    with _engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    return [dict(row) for row in rows]