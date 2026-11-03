import os
from typing import List, Optional, Literal
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, conint, confloat, constr, validator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida")

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, future=True)

app = FastAPI()

class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

class QueryParams(BaseModel):
    nome: Optional[constr(strip_whitespace=True, min_length=1)] = None
    categoria: Optional[constr(strip_whitespace=True, min_length=1)] = None
    preco_min: Optional[confloat(ge=0)] = None
    preco_max: Optional[confloat(ge=0)] = None
    ordenar_por: Optional[Literal["preco", "nome"]] = None

    @validator("preco_max")
    def preco_max_maior_que_min(cls, v, values):
        if v is not None and values.get("preco_min") is not None and v < values["preco_min"]:
            raise ValueError("preco_max deve ser maior ou igual a preco_min")
        return v

@app.get("/produtos", response_model=List[Produto])
def buscar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None, ge=0),
    preco_max: Optional[float] = Query(None, ge=0),
    ordenar_por: Optional[str] = Query(None),
):
    # Validação do ordenar_por
    allowed_order_cols = {"preco", "nome"}
    if ordenar_por is not None and ordenar_por not in allowed_order_cols:
        raise HTTPException(status_code=422, detail=f"ordenar_por deve ser um dos: {', '.join(allowed_order_cols)}")

    # Validação preco_min e preco_max
    if preco_min is not None and preco_max is not None and preco_max < preco_min:
        raise HTTPException(status_code=422, detail="preco_max deve ser maior ou igual a preco_min")

    filters = []
    params = {}

    if nome:
        filters.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"
    if categoria:
        filters.append("categoria = :categoria")
        params["categoria"] = categoria
    if preco_min is not None:
        filters.append("preco >= :preco_min")
        params["preco_min"] = preco_min
    if preco_max is not None:
        filters.append("preco <= :preco_max")
        params["preco_max"] = preco_max

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    order_clause = ""
    if ordenar_por:
        order_clause = f"ORDER BY {ordenar_por} ASC"

    query = f"""
        SELECT id, nome, categoria, preco, estoque
        FROM produtos
        {where_clause}
        {order_clause}
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            produtos = [
                Produto(
                    id=row.id,
                    nome=row.nome,
                    categoria=row.categoria,
                    preco=row.preco,
                    estoque=row.estoque,
                )
                for row in result
            ]
    except SQLAlchemyError:
        # Não repassar erros do banco ao cliente
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

    return produtos