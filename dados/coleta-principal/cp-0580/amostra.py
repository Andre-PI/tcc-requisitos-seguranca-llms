import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "")
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ProdutoModel(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String)
    categoria: Mapped[str] = mapped_column(String)
    preco: Mapped[float] = mapped_column(Float)
    estoque: Mapped[int] = mapped_column(Integer)


class ProdutoResponse(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    model_config = ConfigDict(from_attributes=True)


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoResponse])
def get_produtos(
    nome: Optional[str] = None,
    categoria: Optional[str] = None,
    preco_min: Optional[float] = None,
    preco_max: Optional[float] = None,
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    with SessionLocal() as session:
        query = select(ProdutoModel)

        if nome is not None:
            query = query.where(ProdutoModel.nome.contains(nome))
        if categoria is not None:
            query = query.where(ProdutoModel.categoria == categoria)
        if preco_min is not None:
            query = query.where(ProdutoModel.preco >= preco_min)
        if preco_max is not None:
            query = query.where(ProdutoModel.preco <= preco_max)

        if ordenar_por == "preco":
            query = query.order_by(ProdutoModel.preco.asc())
        elif ordenar_por == "nome":
            query = query.order_by(ProdutoModel.nome.asc())

        produtos = session.scalars(query).all()
        return produtos