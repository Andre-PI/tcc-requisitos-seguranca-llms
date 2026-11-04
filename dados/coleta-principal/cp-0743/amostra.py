from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text
import os

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)


@app.get("/produtos")
def listar_produtos(
    nome: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    preco_min: float | None = Query(default=None),
    preco_max: float | None = Query(default=None),
    ordenar_por: str | None = Query(default=None, pattern="^(preco|nome)$"),
):
    where_clauses = []
    params: dict[str, object] = {}

    if nome is not None:
        where_clauses.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"

    if categoria is not None:
        where_clauses.append("categoria = :categoria")
        params["categoria"] = categoria

    if preco_min is not None:
        where_clauses.append("preco >= :preco_min")
        params["preco_min"] = preco_min

    if preco_max is not None:
        where_clauses.append("preco <= :preco_max")
        params["preco_max"] = preco_max

    query = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    if ordenar_por == "preco":
        query += " ORDER BY preco ASC"
    elif ordenar_por == "nome":
        query += " ORDER BY nome ASC"

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        produtos = [dict(row._mapping) for row in result.fetchall()]

    return produtos