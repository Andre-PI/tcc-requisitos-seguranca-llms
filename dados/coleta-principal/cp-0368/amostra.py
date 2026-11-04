import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///test.db")
if not db_path.startswith("sqlite:///"):
    database_url = f"sqlite:///{db_path}"
else:
    database_url = db_path

engine = create_engine(database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String)
    categoria: Mapped[str] = mapped_column(String)
    preco: Mapped[float] = mapped_column(Float)
    estoque: Mapped[int] = mapped_column(Integer)


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoOut])
def listar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
):
    stmt = select(Produto)

    if nome:
        stmt = stmt.where(Produto.nome.contains(nome))
    if categoria:
        stmt = stmt.where(Produto.categoria == categoria)
    if preco_min is not None:
        stmt = stmt.where(Produto.preco >= preco_min)
    if preco_max is not None:
        stmt = stmt.where(Produto.preco <= preco_max)

    if ordenar_por == "preco":
        stmt = stmt.order_by(Produto.preco.asc())
    elif ordenar_por == "nome":
        stmt = stmt.order_by(Produto.nome.asc())

    with SessionLocal() as session:
        produtos = session.scalars(stmt).all()
        return produtos