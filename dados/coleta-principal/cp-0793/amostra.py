import os
from typing import List, Literal, Optional
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "produtos.db")
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ProdutoDB(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    categoria = Column(String)
    preco = Column(Float)
    estoque = Column(Integer)


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
    nome: Optional[str] = Query(None, min_length=1),
    categoria: Optional[str] = Query(None, min_length=1),
    preco_min: Optional[float] = Query(None, ge=0.0),
    preco_max: Optional[float] = Query(None, ge=0.0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None)
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preco_min nao pode ser maior que preco_max"
        )

    try:
        with SessionLocal() as session:
            stmt = select(ProdutoDB)

            if nome:
                escaped_nome = nome.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                stmt = stmt.where(ProdutoDB.nome.ilike(f"%{escaped_nome}%", escape="\\"))

            if categoria:
                stmt = stmt.where(ProdutoDB.categoria == categoria)

            if preco_min is not None:
                stmt = stmt.where(ProdutoDB.preco >= preco_min)

            if preco_max is not None:
                stmt = stmt.where(ProdutoDB.preco <= preco_max)

            colunas_permitidas = {
                "preco": ProdutoDB.preco,
                "nome": ProdutoDB.nome
            }

            if ordenar_por:
                coluna = colunas_permitidas[ordenar_por]
                stmt = stmt.order_by(coluna.asc())

            results = session.scalars(stmt).all()
            return results
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a solicitacao"
        )