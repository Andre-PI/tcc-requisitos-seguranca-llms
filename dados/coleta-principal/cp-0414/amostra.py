import os
from typing import List, Literal, Optional
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Column, Float, Integer, String, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./produtos.db")
if not db_path.startswith("sqlite://"):
    db_path = f"sqlite:///{db_path}"

engine = create_engine(db_path, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    categoria = Column(String)
    preco = Column(Float)
    estoque = Column(Integer)


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    class Config:
        from_attributes = True


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoOut], status_code=status.HTTP_200_OK)
def buscar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None, ge=0),
    preco_max: Optional[float] = Query(None, ge=0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
):
    try:
        with SessionLocal() as db:
            query = select(Produto)

            if nome is not None:
                escaped_nome = (
                    nome.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                )
                query = query.where(
                    Produto.nome.ilike(f"%{escaped_nome}%", escape="\\")
                )

            if categoria is not None:
                query = query.where(Produto.categoria == categoria)

            if preco_min is not None:
                query = query.where(Produto.preco >= preco_min)

            if preco_max is not None:
                query = query.where(Produto.preco <= preco_max)

            colunas_ordenacao = {
                "preco": Produto.preco.asc(),
                "nome": Produto.nome.asc(),
            }

            if ordenar_por in colunas_ordenacao:
                query = query.order_by(colunas_ordenacao[ordenar_por])

            produtos = db.scalars(query).all()
            return produtos
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a consulta.",
        )