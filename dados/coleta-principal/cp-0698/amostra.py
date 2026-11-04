import os
from decimal import Decimal
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, confloat, conint
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


NomeQuery = Annotated[Optional[str], Query(default=None, min_length=1, max_length=255)]
CategoriaQuery = Annotated[Optional[str], Query(default=None, min_length=1, max_length=255)]
PrecoMinQuery = Annotated[Optional[confloat(ge=0)], Query(default=None)]
PrecoMaxQuery = Annotated[Optional[confloat(ge=0)], Query(default=None)]
OrdenarPorQuery = Annotated[Optional[Literal["preco", "nome"]], Query(default=None)]


@app.get("/produtos", response_model=list[ProdutoOut])
def buscar_produtos(
    nome: NomeQuery = None,
    categoria: CategoriaQuery = None,
    preco_min: PrecoMinQuery = None,
    preco_max: PrecoMaxQuery = None,
    ordenar_por: OrdenarPorQuery = None,
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=422, detail="preco_min não pode ser maior que preco_max")

    sql = """
        SELECT id, nome, categoria, preco, estoque
        FROM produtos
        WHERE 1=1
    """
    params: dict[str, object] = {}

    if nome is not None:
        sql += " AND nome LIKE :nome"
        params["nome"] = f"%{nome}%"

    if categoria is not None:
        sql += " AND categoria = :categoria"
        params["categoria"] = categoria

    if preco_min is not None:
        sql += " AND preco >= :preco_min"
        params["preco_min"] = float(preco_min)

    if preco_max is not None:
        sql += " AND preco <= :preco_max"
        params["preco_max"] = float(preco_max)

    order_map = {
        "preco": "preco ASC",
        "nome": "nome ASC",
    }
    if ordenar_por is not None:
        sql += f" ORDER BY {order_map[ordenar_por]}"

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params)
            rows = result.mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar produtos")

    return [
        ProdutoOut(
            id=row["id"],
            nome=row["nome"],
            categoria=row["categoria"],
            preco=float(row["preco"]) if row["preco"] is not None else 0.0,
            estoque=row["estoque"],
        )
        for row in rows
    ]