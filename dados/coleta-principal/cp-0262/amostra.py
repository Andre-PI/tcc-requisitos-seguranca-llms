import os
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

app = FastAPI()


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


PrecoMin = Annotated[Optional[float], Query(default=None, ge=0)]
PrecoMax = Annotated[Optional[float], Query(default=None, ge=0)]
OrdenarPor = Annotated[Optional[Literal["preco", "nome"]], Query(default=None)]


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None, min_length=1, max_length=255)] = None,
    categoria: Annotated[Optional[str], Query(default=None, min_length=1, max_length=255)] = None,
    preco_min: PrecoMin = None,
    preco_max: PrecoMax = None,
    ordenar_por: OrdenarPor = None,
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=422, detail="preco_min não pode ser maior que preco_max")

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

    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

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
        raise HTTPException(status_code=500, detail="Erro interno no servidor")

    return [ProdutoOut(**row) for row in rows]