import os
from typing import Optional, Literal

from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field, field_validator
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


class ProdutoFiltro(BaseModel):
    nome: Optional[str] = None
    categoria: Optional[str] = None
    preco_min: Optional[float] = Field(default=None, ge=0)
    preco_max: Optional[float] = Field(default=None, ge=0)
    ordenar_por: Optional[Literal["preco", "nome"]] = None

    @field_validator("nome", "categoria")
    @classmethod
    def strip_empty(cls, v):
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("preco_max")
    @classmethod
    def validate_range(cls, v, info):
        preco_min = info.data.get("preco_min")
        if v is not None and preco_min is not None and v < preco_min:
            raise ValueError("preco_max deve ser maior ou igual a preco_min")
        return v


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None, ge=0),
    preco_max: Optional[float] = Query(default=None, ge=0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    try:
        filtros = ProdutoFiltro(
            nome=nome,
            categoria=categoria,
            preco_min=preco_min,
            preco_max=preco_max,
            ordenar_por=ordenar_por,
        )
    except Exception:
        raise HTTPException(status_code=422, detail="Parâmetros inválidos")

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

    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    order_map = {
        "preco": "preco ASC",
        "nome": "nome ASC",
    }
    if filtros.ordenar_por is not None:
        sql += f" ORDER BY {order_map[filtros.ordenar_por]}"

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params)
            rows = result.mappings().all()
        return [ProdutoOut(**row) for row in rows]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar produtos")