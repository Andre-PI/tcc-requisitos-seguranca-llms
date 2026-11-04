import os
from decimal import Decimal
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()


DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definida")

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    future=True,
    pool_pre_ping=True,
)


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


class BuscaProdutosParams(BaseModel):
    nome: Optional[str] = None
    categoria: Optional[str] = None
    preco_min: Optional[float] = Field(default=None, ge=0)
    preco_max: Optional[float] = Field(default=None, ge=0)
    ordenar_por: Optional[Literal["preco", "nome"]] = None

    @field_validator("nome", "categoria")
    @classmethod
    def strip_text(cls, v):
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("preco_max")
    @classmethod
    def validate_price_range(cls, v, info):
        preco_min = info.data.get("preco_min")
        if v is not None and preco_min is not None and v < preco_min:
            raise ValueError("preco_max deve ser maior ou igual a preco_min")
        return v


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None)] = None,
    categoria: Annotated[Optional[str], Query(default=None)] = None,
    preco_min: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    preco_max: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    ordenar_por: Annotated[Optional[Literal["preco", "nome"]], Query(default=None)] = None,
):
    try:
        params = BuscaProdutosParams(
            nome=nome,
            categoria=categoria,
            preco_min=preco_min,
            preco_max=preco_max,
            ordenar_por=ordenar_por,
        )
    except Exception:
        raise HTTPException(status_code=422, detail="Parâmetros inválidos")

    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    where_clauses = []
    bind_params = {}

    if params.nome is not None:
        where_clauses.append("nome LIKE :nome")
        bind_params["nome"] = f"%{params.nome}%"

    if params.categoria is not None:
        where_clauses.append("categoria = :categoria")
        bind_params["categoria"] = params.categoria

    if params.preco_min is not None:
        where_clauses.append("preco >= :preco_min")
        bind_params["preco_min"] = params.preco_min

    if params.preco_max is not None:
        where_clauses.append("preco <= :preco_max")
        bind_params["preco_max"] = params.preco_max

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    order_map = {
        "preco": "preco ASC",
        "nome": "nome ASC",
    }
    if params.ordenar_por is not None:
        sql += f" ORDER BY {order_map[params.ordenar_por]}"

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), bind_params)
            rows = result.mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar produtos")

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