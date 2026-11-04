import os
from typing import List, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_url = f"sqlite:///{db_path}"
else:
    db_url = db_path

engine = create_engine(db_url, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class ProdutoModel(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    categoria: Mapped[str]
    preco: Mapped[float]
    estoque: Mapped[int]


class ProdutoSchema(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    class Config:
        from_attributes = True


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoSchema])
def listar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[str] = Query(None, pattern="^(preco|nome)$"),
):
    stmt = select(ProdutoModel)

    if nome:
        stmt = stmt.where(ProdutoModel.nome.like(f"%{nome}%"))
    if categoria:
        stmt = stmt.where(ProdutoModel.categoria == categoria)
    if preco_min is not None:
        stmt = stmt.where(ProdutoModel.preco >= preco_min)
    if preco_max is not None:
        stmt = stmt.where(ProdutoModel.preco <= preco_max)

    if ordenar_por == "preco":
        stmt = stmt.order_by(ProdutoModel.preco.asc())
    elif ordenar_por == "nome":
        stmt = stmt.order_by(ProdutoModel.nome.asc())

    with Session(engine) as session:
        produtos = session.scalars(stmt).all()
        return produtos