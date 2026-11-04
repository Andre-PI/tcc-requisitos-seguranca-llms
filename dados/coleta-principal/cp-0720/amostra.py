import os
from typing import Optional, List

from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, select, and_, asc
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
metadata = MetaData()

try:
    produtos = Table("produtos", metadata, autoload_with=engine)
except Exception as e:
    raise RuntimeError(f"Falha ao carregar tabela produtos: {e}") from e


class ProdutoOut(BaseModel):
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
    conditions = []

    if nome is not None:
        conditions.append(produtos.c.nome.ilike(f"%{nome}%"))
    if categoria is not None:
        conditions.append(produtos.c.categoria == categoria)
    if preco_min is not None:
        conditions.append(produtos.c.preco >= preco_min)
    if preco_max is not None:
        conditions.append(produtos.c.preco <= preco_max)

    stmt = select(
        produtos.c.id,
        produtos.c.nome,
        produtos.c.categoria,
        produtos.c.preco,
        produtos.c.estoque,
    )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    if ordenar_por == "preco":
        stmt = stmt.order_by(asc(produtos.c.preco))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(produtos.c.nome))

    try:
        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [ProdutoOut(**row) for row in rows]
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail="Erro ao consultar produtos") from e