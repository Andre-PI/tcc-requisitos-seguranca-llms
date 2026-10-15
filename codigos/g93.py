from __future__ import annotations

import os
from decimal import Decimal
from typing import Annotated, Literal, Optional

from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, Numeric, String, and_, asc, create_engine, select
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

Base = declarative_base()


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False, index=True)
    categoria = Column(String(255), nullable=False, index=True)
    preco = Column(Numeric(10, 2), nullable=False, index=True)
    estoque = Column(Integer, nullable=False)


class ProdutoResponse(BaseModel):
    id: int
    nome: str = Field(max_length=255)
    categoria: str = Field(max_length=255)
    preco: Decimal
    estoque: int

    class Config:
        from_attributes = True


app = FastAPI(title="API de Produtos")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/produtos", response_model=list[ProdutoResponse])
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None, min_length=1, max_length=255)] = None,
    categoria: Annotated[Optional[str], Query(default=None, min_length=1, max_length=255)] = None,
    preco_min: Annotated[Optional[Decimal], Query(default=None, ge=0)] = None,
    preco_max: Annotated[Optional[Decimal], Query(default=None, ge=0)] = None,
    ordenar_por: Annotated[Optional[Literal["preco", "nome"]], Query(default=None)] = None,
    db: Session = Depends(get_db),
):
    filtros = []

    if nome is not None:
        filtros.append(Produto.nome.ilike(f"%{nome}%"))
    if categoria is not None:
        filtros.append(Produto.categoria == categoria)
    if preco_min is not None:
        filtros.append(Produto.preco >= preco_min)
    if preco_max is not None:
        filtros.append(Produto.preco <= preco_max)

    stmt = select(Produto)

    if filtros:
        stmt = stmt.where(and_(*filtros))

    if ordenar_por == "preco":
        stmt = stmt.order_by(asc(Produto.preco), asc(Produto.id))
    elif ordenar_por == "nome":
        stmt = stmt.order_by(asc(Produto.nome), asc(Produto.id))
    else:
        stmt = stmt.order_by(asc(Produto.id))

    return db.execute(stmt).scalars().all()