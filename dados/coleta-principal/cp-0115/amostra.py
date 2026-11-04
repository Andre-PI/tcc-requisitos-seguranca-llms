import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel
from sqlalchemy import Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_path = f"sqlite:///{db_path}"

engine = create_engine(db_path, connect_args={"check_same_thread": False})
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
    nome: Optional[str] = None,
    categoria: Optional[str] = None,
    preco_min: Optional[float] = None,
    preco_max: Optional[float] = None,
    ordenar_por: Optional[Literal["preco", "nome"]] = None,
):
    with SessionLocal() as session:
        query = select(ProdutoModel)

        if nome:
            query = query.where(ProdutoModel.nome.like(f"%{nome}%"))
        if categoria:
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