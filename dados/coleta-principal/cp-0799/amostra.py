import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict
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


class ProdutoDB(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    categoria: Mapped[str]
    preco: Mapped[float]
    estoque: Mapped[int]


class ProdutoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoSchema])
def get_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
):
    stmt = select(ProdutoDB)

    if nome:
        stmt = stmt.where(ProdutoDB.nome.contains(nome))
    if categoria:
        stmt = stmt.where(ProdutoDB.categoria == categoria)
    if preco_min is not None:
        stmt = stmt.where(ProdutoDB.preco >= preco_min)
    if preco_max is not None:
        stmt = stmt.where(ProdutoDB.preco <= preco_max)

    if ordenar_por == "preco":
        stmt = stmt.order_by(ProdutoDB.preco.asc())
    elif ordenar_por == "nome":
        stmt = stmt.order_by(ProdutoDB.nome.asc())

    with Session(engine) as session:
        produtos = session.scalars(stmt).all()
        return produtos