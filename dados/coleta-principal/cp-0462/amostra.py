import os
from typing import List, Literal, Optional
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, Numeric, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = os.environ.get("TCC_DB_PATH", "produtos.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ProdutoModel(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True)
    nome = Column(String)
    categoria = Column(String)
    preco = Column(Numeric)
    estoque = Column(Integer)


class ProdutoResponse(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    model_config = ConfigDict(from_attributes=True)


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoResponse], status_code=status.HTTP_200_OK)
def buscar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
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

    if nome:
        escaped_nome = nome.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(ProdutoModel.nome.ilike(f"%{escaped_nome}%", escape="\\"))

    if categoria:
        stmt = stmt.where(ProdutoModel.categoria == categoria)

    if preco_min is not None:
        stmt = stmt.where(ProdutoModel.preco >= preco_min)

    if preco_max is not None:
        stmt = stmt.where(ProdutoModel.preco <= preco_max)

    allowed_sort_columns = {
        "preco": ProdutoModel.preco.asc(),
        "nome": ProdutoModel.nome.asc()
    }

    if ordenar_por:
        stmt = stmt.order_by(allowed_sort_columns[ordenar_por])

    try:
        with SessionLocal() as session:
            produtos = session.scalars(stmt).all()
            return produtos
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a consulta."
        )