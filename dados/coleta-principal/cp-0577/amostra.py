import os
from decimal import Decimal
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, condecimal
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

app = FastAPI()


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


NomeQuery = Annotated[
    str | None,
    Query(default=None, min_length=1, max_length=255, description="Busca parcial por nome"),
]
CategoriaQuery = Annotated[
    str | None,
    Query(default=None, min_length=1, max_length=255),
]
PrecoQuery = Annotated[
    condecimal(ge=0, max_digits=12, decimal_places=2) | None,
    Query(default=None),
]
OrdenarPorQuery = Annotated[
    str | None,
    Query(default=None, pattern="^(preco|nome)$"),
]


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: NomeQuery = None,
    categoria: CategoriaQuery = None,
    preco_min: PrecoQuery = None,
    preco_max: PrecoQuery = None,
    ordenar_por: OrdenarPorQuery = None,
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=422, detail="preco_min não pode ser maior que preco_max")

    order_map = {
        None: "nome",
        "nome": "nome",
        "preco": "preco",
    }
    order_column = order_map.get(ordenar_por)
    if order_column is None:
        raise HTTPException(status_code=422, detail="ordenar_por inválido")

    conditions = []
    params: dict[str, Any] = {}

    if nome is not None:
        conditions.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"
    if categoria is not None:
        conditions.append("categoria = :categoria")
        params["categoria"] = categoria
    if preco_min is not None:
        conditions.append("preco >= :preco_min")
        params["preco_min"] = float(preco_min)
    if preco_max is not None:
        conditions.append("preco <= :preco_max")
        params["preco_max"] = float(preco_max)

    where_sql = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT id, nome, categoria, preco, estoque
        FROM produtos
        {where_sql}
        ORDER BY {order_column} ASC
    """

    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno no servidor")

    return [
        ProdutoOut(
            id=row["id"],
            nome=row["nome"],
            categoria=row["categoria"],
            preco=float(row["preco"]),
            estoque=row["estoque"],
        )
        for row in rows
    ]