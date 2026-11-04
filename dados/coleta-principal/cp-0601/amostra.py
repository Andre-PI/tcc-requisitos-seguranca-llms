from fastapi import FastAPI, Query
from sqlalchemy import create_engine, MetaData, Table, select, and_, asc
from sqlalchemy.engine import Engine
import os

app = FastAPI()

db_path = os.getenv("TCC_DB_PATH")
if not db_path:
    raise RuntimeError("TCC_DB_PATH não definido")

engine: Engine = create_engine(f"sqlite:///{db_path}", future=True)
metadata = MetaData()
produtos = Table("produtos", metadata, autoload_with=engine)


@app.get("/produtos")
def listar_produtos(
    nome: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    preco_min: float | None = Query(default=None),
    preco_max: float | None = Query(default=None),
    ordenar_por: str | None = Query(default=None),
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
        stmt = stmt.order_by(asc(produtos.c.preco))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(produtos.c.nome))

    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    return [dict(row) for row in rows]