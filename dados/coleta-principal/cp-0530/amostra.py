import os
from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Float, Integer, String, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

db_path = os.getenv("TCC_DB_PATH", "produtos.db")
DATABASE_URL = f"sqlite:///{db_path}"

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
    preco = Column(Float)
    estoque = Column(Integer)


class ProdutoSchema(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    model_config = ConfigDict(from_attributes=True)


class OrdenacaoEnum(str, Enum):
    preco = "preco"
    nome = "nome"


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoSchema], status_code=status.HTTP_200_OK)
def buscar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None, ge=0.0),
    preco_max: Optional[float] = Query(default=None, ge=0.0),
    ordenar_por: Optional[OrdenacaoEnum] = Query(default=None),
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preco_min nao pode ser maior que preco_max",
        )

    try:
        with SessionLocal() as session:
            stmt = select(ProdutoModel)

            if nome is not None:
                escaped_nome = nome.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                stmt = stmt.where(ProdutoModel.nome.ilike(f"%{escaped_nome}%", escape="\\"))

            if categoria is not None:
                stmt = stmt.where(ProdutoModel.categoria == categoria)

            if preco_min is not None:
                stmt = stmt.where(ProdutoModel.preco >= preco_min)

            if preco_max is not None:
                stmt = stmt.where(ProdutoModel.preco <= preco_max)

            if ordenar_por == OrdenacaoEnum.preco:
                stmt = stmt.order_by(ProdutoModel.preco.asc())
            elif ordenar_por == OrdenacaoEnum.nome:
                stmt = stmt.order_by(ProdutoModel.nome.asc())

            produtos = session.scalars(stmt).all()
            return produtos

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno no servidor ao processar a consulta.",
        )