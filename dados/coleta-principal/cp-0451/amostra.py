import os
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

ENGINE = create_engine(f"sqlite:///{DB_PATH}", future=True)


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


class FiltrosConsulta(BaseModel):
    nome: Optional[str] = None
    categoria: Optional[str] = None
    preco_min: Optional[float] = Field(default=None, ge=0)
    preco_max: Optional[float] = Field(default=None, ge=0)
    ordenar_por: Optional[Literal["preco", "nome"]] = None


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None, min_length=1)] = None,
    categoria: Annotated[Optional[str], Query(default=None, min_length=1)] = None,
    preco_min: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    preco_max: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    ordenar_por: Annotated[Optional[Literal["preco", "nome"]], Query(default=None)] = None,
):
    try:
        filtros = FiltrosConsulta(
            nome=nome,
            categoria=categoria,
            preco_min=preco_min,
            preco_max=preco_max,
            ordenar_por=ordenar_por,
        )
    except ValidationError:
        raise HTTPException(status_code=422, detail="Parâmetros inválidos")

    if filtros.preco_min is not None and filtros.preco_max is not None and filtros.preco_min > filtros.preco_max:
        raise HTTPException(status_code=422, detail="preco_min não pode ser maior que preco_max")

    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    where_clauses = []
    params = {}

    if filtros.nome is not None:
        where_clauses.append("nome LIKE :nome")
        params["nome"] = f"%{filtros.nome}%"
    if filtros.categoria is not None:
        where_clauses.append("categoria = :categoria")
        params["categoria"] = filtros.categoria
    if filtros.preco_min is not None:
        where_clauses.append("preco >= :preco_min")
        params["preco_min"] = filtros.preco_min
    if filtros.preco_max is not None:
        where_clauses.append("preco <= :preco_max")
        params["preco_max"] = filtros.preco_max

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    if filtros.ordenar_por is not None:
        order_map = {"preco": "preco", "nome": "nome"}
        sql += f" ORDER BY {order_map[filtros.ordenar_por]} ASC"

    try:
        with ENGINE.connect() as conn:
            result = conn.execute(text(sql), params)
            rows = result.mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar o banco de dados")

    return [ProdutoOut(**row) for row in rows]