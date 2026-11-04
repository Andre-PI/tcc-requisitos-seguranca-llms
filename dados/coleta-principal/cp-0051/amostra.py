import os
from typing import Optional, List

from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

app = FastAPI()

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

db_url = f"sqlite:///{DB_PATH}"
engine: Engine = create_engine(db_url, future=True)


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


@app.get("/produtos", response_model=List[ProdutoOut])
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[str] = Query(default=None, pattern="^(preco|nome)$"),
):
    query = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    conditions = []
    params = {}

    if nome is not None:
        conditions.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"
    if categoria is not None:
        conditions.append("categoria = :categoria")
        params["categoria"] = categoria
    if preco_min is not None:
        conditions.append("preco >= :preco_min")
        params["preco_min"] = preco_min
    if preco_max is not None:
        conditions.append("preco <= :preco_max")
        params["preco_max"] = preco_max

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    if ordenar_por == "preco":
        query += " ORDER BY preco ASC"
    elif ordenar_por == "nome":
        query += " ORDER BY nome ASC"

    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.mappings().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao consultar produtos") from e

    return [ProdutoOut(**row) for row in rows]