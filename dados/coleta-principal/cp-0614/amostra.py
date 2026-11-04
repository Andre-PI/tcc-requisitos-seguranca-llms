import os
from decimal import Decimal
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
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
    nome: Optional[str] = None
    categoria: Optional[str] = None
    preco_min: Optional[float] = Field(default=None, ge=0)
    preco_max: Optional[float] = Field(default=None, ge=0)
    ordenar_por: Optional[Literal["preco", "nome"]] = None

    @field_validator("nome", "categoria")
    @classmethod
    def validar_texto(cls, v):
        if v is None:
            return v
        v = v.strip()
        return v or None

    @model_validator(mode="after")
    def validar_faixa_preco(self):
        if self.preco_min is not None and self.preco_max is not None and self.preco_min > self.preco_max:
            raise ValueError("preco_min não pode ser maior que preco_max")
        return self


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None, ge=0),
    preco_max: Optional[float] = Query(default=None, ge=0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    try:
        params = ProdutoQuery(
            nome=nome,
            categoria=categoria,
            preco_min=preco_min,
            preco_max=preco_max,
            ordenar_por=ordenar_por,
        )
    except Exception:
        raise HTTPException(status_code=422, detail="Parâmetros inválidos")

    where = []
    bind_params = {}

    if params.nome is not None:
        where.append("nome LIKE :nome")
        bind_params["nome"] = f"%{params.nome}%"

    if params.categoria is not None:
        where.append("categoria = :categoria")
        bind_params["categoria"] = params.categoria

    if params.preco_min is not None:
        where.append("preco >= :preco_min")
        bind_params["preco_min"] = params.preco_min

    if params.preco_max is not None:
        where.append("preco <= :preco_max")
        bind_params["preco_max"] = params.preco_max

    sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    if where:
        sql += " WHERE " + " AND ".join(where)

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
            preco=row["preco"],
            estoque=row["estoque"],
        )
        for row in rows
    ]