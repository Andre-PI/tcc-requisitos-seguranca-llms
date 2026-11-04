import os
from typing import Optional, Literal

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, MetaData, Table, select, and_

app = FastAPI()

db_path = os.environ.get("TCC_DB_PATH", "")
if db_path.startswith("sqlite:///"):
    database_url = db_path
else:
    database_url = f"sqlite:///{db_path}"

engine = create_engine(database_url, future=True)
metadata = MetaData()
produtos = Table("produtos", metadata, autoload_with=engine)


@app.get("/produtos")
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    condicoes = []

    if nome is not None:
        condicoes.append(produtos.c.nome.ilike(f"%{nome}%"))
    if categoria is not None:
        condicoes.append(produtos.c.categoria == categoria)
    if preco_min is not None:
        condicoes.append(produtos.c.preco >= preco_min)
    if preco_max is not None:
        condicoes.append(produtos.c.preco <= preco_max)

    stmt = select(
        produtos.c.id,
        produtos.c.nome,
        produtos.c.categoria,
        produtos.c.preco,
        produtos.c.estoque,
    )

    if condicoes:
        stmt = stmt.where(and_(*condicoes))

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