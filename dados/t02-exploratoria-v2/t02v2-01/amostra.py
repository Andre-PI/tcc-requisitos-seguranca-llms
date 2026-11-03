import os
from typing import Optional, Literal

from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, MetaData, Table, select, and_, asc
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida.")

if DB_PATH.startswith("sqlite:///") or DB_PATH.startswith("sqlite://"):
    DATABASE_URL = DB_PATH
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, future=True)
metadata = MetaData()

produtos = Table("produtos", metadata, autoload_with=engine)


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    conditions = []

    if nome is not None:
        conditions.append(produtos.c.nome.like(f"%{nome}%"))
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
        raise HTTPException(status_code=500, detail="Erro ao acessar o banco de dados") from e