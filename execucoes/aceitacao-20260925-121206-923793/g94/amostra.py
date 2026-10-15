from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DECIMAL, Column, Integer, String, asc, create_engine, desc, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./app.db"

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False, index=True)
    categoria = Column(String(255), nullable=False, index=True)
    preco = Column(DECIMAL(10, 2), nullable=False, index=True)
    estoque = Column(Integer, nullable=False)


class OrdenarPor(str, Enum):
    preco = "preco"
    nome = "nome"


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    nome: str = Field(min_length=1, max_length=255)
    categoria: str = Field(min_length=1, max_length=255)
    preco: Decimal
    estoque: int


app = FastAPI(title="API de Produtos")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    categoria: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    preco_min: Annotated[Decimal | None, Query(ge=0)] = None,
    preco_max: Annotated[Decimal | None, Query(ge=0)] = None,
    ordenar_por: Annotated[OrdenarPor | None, Query()] = None,
    db: Session = Depends(get_db),
) -> list[Produto]:
    query = select(Produto)
    filtros: list[Any] = []

    if nome is not None:
        filtros.append(Produto.nome.ilike(f"%{nome}%"))
    if categoria is not None:
        filtros.append(Produto.categoria == categoria)
    if preco_min is not None:
        filtros.append(Produto.preco >= preco_min)
    if preco_max is not None:
        filtros.append(Produto.preco <= preco_max)

    if filtros:
        query = query.where(*filtros)

    if ordenar_por == OrdenarPor.preco:
        query = query.order_by(asc(Produto.preco), asc(Produto.id))
    elif ordenar_por == OrdenarPor.nome:
        query = query.order_by(asc(Produto.nome), asc(Produto.id))
    else:
        query = query.order_by(asc(Produto.id))

    try:
        return list(db.execute(query).scalars().all())
    except SQLAlchemyError:
        return []