import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

db_path = os.getenv("TCC_DB_PATH", "produtos.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

class Base(DeclarativeBase):
    pass

class ProdutoModel(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column()
    categoria: Mapped[str] = mapped_column()
    preco: Mapped[float] = mapped_column()
    estoque: Mapped[int] = mapped_column()

class ProdutoResponse(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    model_config = ConfigDict(from_attributes=True)

app = FastAPI()

def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

@app.get("/produtos", response_model=List[ProdutoResponse])
def get_produtos(
    nome: Optional[str] = Query(None, max_length=100),
    categoria: Optional[str] = Query(None, max_length=100),
    preco_min: Optional[float] = Query(None, ge=0.0),
    preco_max: Optional[float] = Query(None, ge=0.0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None)
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preco_min não pode ser maior que preco_max"
        )

    stmt = select(ProdutoModel)

    if nome is not None:
        escaped_nome = escape_like(nome)
        stmt = stmt.where(ProdutoModel.nome.like(f"%{escaped_nome}%", escape="\\"))

    if categoria is not None:
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