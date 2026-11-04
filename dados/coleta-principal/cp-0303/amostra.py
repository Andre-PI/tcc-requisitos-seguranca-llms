import os
from typing import List, Optional
from enum import Enum
from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, select
from sqlalchemy.orm import declarative_base, sessionmaker

db_path = os.getenv("TCC_DB_PATH", "produtos.db")
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class ProdutoDB(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    categoria = Column(String)
    preco = Column(Float)
    estoque = Column(Integer)


class OrdemEnum(str, Enum):
    preco = "preco"
    nome = "nome"


class ProdutoResponse(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    class Config:
        from_attributes = True


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoResponse], status_code=status.HTTP_200_OK)
def buscar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None, ge=0.0),
    preco_max: Optional[float] = Query(None, ge=0.0),
    ordenar_por: Optional[OrdemEnum] = Query(None),
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preco_min nao pode ser maior que preco_max",
        )

    db = SessionLocal()
    try:
        query = select(ProdutoDB)

        if nome:
            escaped_nome = (
                nome.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            query = query.where(ProdutoDB.nome.ilike(f"%{escaped_nome}%", escape="\\"))

        if categoria:
            query = query.where(ProdutoDB.categoria == categoria)

        if preco_min is not None:
            query = query.where(ProdutoDB.preco >= preco_min)

        if preco_max is not None:
            query = query.where(ProdutoDB.preco <= preco_max)

        if ordenar_por == OrdemEnum.preco:
            query = query.order_by(ProdutoDB.preco.asc())
        elif ordenar_por == OrdemEnum.nome:
            query = query.order_by(ProdutoDB.nome.asc())

        produtos = db.scalars(query).all()
        return produtos
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a solicitacao.",
        )
    finally:
        db.close()