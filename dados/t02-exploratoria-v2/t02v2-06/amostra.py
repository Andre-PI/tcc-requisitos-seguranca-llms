import os
from decimal import Decimal

from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite+pysqlite:///{DB_PATH}", future=True)


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


class ProdutoQuery(BaseModel):
    nome: str | None = None
    categoria: str | None = None
    preco_min: Decimal | None = Field(default=None)
    preco_max: Decimal | None = Field(default=None)
    ordenar_por: str | None = Field(default=None)

    @field_validator("nome", "categoria")
    @classmethod
    def validar_texto(cls, v):
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("preco_min", "preco_max")
    @classmethod
    def validar_preco(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("preço inválido")
        if v > Decimal("1000000000"):
            raise ValueError("preço inválido")
        return v

    @field_validator("ordenar_por")
    @classmethod
    def validar_ordenar_por(cls, v):
        if v is None:
            return v
        v = v.strip().lower()
        if v not in {"preco", "nome"}:
            raise ValueError("ordenar_por inválido")
        return v


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    preco_min: float | None = Query(default=None),
    preco_max: float | None = Query(default=None),
    ordenar_por: str | None = Query(default=None),
):
    try:
        query = ProdutoQuery(
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
    params: dict[str, object] = {}

    if query.nome is not None:
        where_clauses.append("nome LIKE :nome")
        params["nome"] = f"%{query.nome}%"
    if query.categoria is not None:
        where_clauses.append("categoria = :categoria")
        params["categoria"] = query.categoria
    if query.preco_min is not None:
        where_clauses.append("preco >= :preco_min")
        params["preco_min"] = float(query.preco_min)
    if query.preco_max is not None:
        where_clauses.append("preco <= :preco_max")
        params["preco_max"] = float(query.preco_max)

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    order_map = {"preco": "preco", "nome": "nome"}
    if query.ordenar_por is not None:
        sql += f" ORDER BY {order_map[query.ordenar_por]} ASC"

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params)
            rows = result.mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar produtos")

    return [ProdutoOut(**row) for row in rows]