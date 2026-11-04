import os
from typing import Optional, Literal

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida.")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)


@app.get("/produtos")
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    sql = [
        "SELECT id, nome, categoria, preco, estoque",
        "FROM produtos",
    ]
    where = []
    params = {}

    if nome is not None:
        where.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"
    if categoria is not None:
        where.append("categoria = :categoria")
        params["categoria"] = categoria
    if preco_min is not None:
        where.append("preco >= :preco_min")
        params["preco_min"] = preco_min
    if preco_max is not None:
        where.append("preco <= :preco_max")
        params["preco_max"] = preco_max

    if where:
        sql.append("WHERE " + " AND ".join(where))

    if ordenar_por == "preco":
        sql.append("ORDER BY preco ASC")
    elif ordenar_por == "nome":
        sql.append("ORDER BY nome ASC")

    query = " ".join(sql)

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()

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