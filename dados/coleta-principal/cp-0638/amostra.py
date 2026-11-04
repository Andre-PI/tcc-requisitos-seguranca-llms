import os
from decimal import Decimal
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

app = FastAPI()


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


class QueryParams(BaseModel):
    nome: str | None = None
    categoria: str | None = None
    preco_min: Decimal | None = None
    preco_max: Decimal | None = None
    ordenar_por: Literal["preco", "nome"] | None = None

    @field_validator("nome", "categoria")
    @classmethod
    def validar_texto(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("preco_min", "preco_max")
    @classmethod
    def validar_preco(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        if v < 0:
            raise ValueError("preço deve ser não negativo")
        if v > Decimal("1000000000"):
            raise ValueError("preço fora da faixa permitida")
        return v


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    preco_min: float | None = Query(default=None),
    preco_max: float | None = Query(default=None),
    ordenar_por: Literal["preco", "nome"] | None = Query(default=None),
):
    try:
        params = QueryParams(
            nome=nome,
            categoria=categoria,
            preco_min=preco_min,
            preco_max=preco_max,
            ordenar_por=ordenar_por,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail="Parâmetros inválidos") from e

    if params.preco_min is not None and params.preco_max is not None and params.preco_min > params.preco_max:
        raise HTTPException(status_code=422, detail="preco_min não pode ser maior que preco_max")

    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    where_clauses: list[str] = []
    bind_params: dict[str, Any] = {}

    if params.nome is not None:
        where_clauses.append("nome LIKE :nome")
        bind_params["nome"] = f"%{params.nome}%"

    if params.categoria is not None:
        where_clauses.append("categoria = :categoria")
        bind_params["categoria"] = params.categoria

    if params.preco_min is not None:
        where_clauses.append("preco >= :preco_min")
        bind_params["preco_min"] = float(params.preco_min)

    if params.preco_max is not None:
        where_clauses.append("preco <= :preco_max")
        bind_params["preco_max"] = float(params.preco_max)

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    order_map = {"preco": "preco", "nome": "nome"}
    if params.ordenar_por is not None:
        sql += f" ORDER BY {order_map[params.ordenar_por]} ASC"

    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql), bind_params).mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar produtos")

    return [ProdutoOut(**row) for row in rows]