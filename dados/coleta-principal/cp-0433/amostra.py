import os
from typing import Optional, List

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, MetaData, Table, select, and_

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

db_url = f"sqlite:///{DB_PATH}"
engine = create_engine(db_url, future=True)

metadata = MetaData()
produtos = Table("produtos", metadata, autoload_with=engine)


@app.get("/produtos")
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[str] = Query(default=None, pattern="^(preco|nome)$"),
):
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
        stmt = stmt.order_by(produtos.c.preco.asc())
    elif ordenar_por == "nome":
        stmt = stmt.order_by(produtos.c.nome.asc())

    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    return [
        {
            "id": row["id"],
            "nome": row["nome"],
            "categoria": row["categoria"],
            "preco": row["preco"],
            "estoque": row["estoque"],
        }
        for row in rows
    ]