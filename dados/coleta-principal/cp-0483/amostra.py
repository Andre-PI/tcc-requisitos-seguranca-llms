import os
from typing import List, Literal, Optional
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Float, Integer, String, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    database_url = f"sqlite:///{db_path}"
else:
    database_url = db_path

engine = create_engine(
    database_url, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ProdutoModel(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
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


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoSchema])
def listar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None, ge=0.0),
    preco_max: Optional[float] = Query(None, ge=0.0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
):
    try:
        with SessionLocal() as session:
            stmt = select(ProdutoModel)

            if nome is not None:
                escaped_nome = (
                    nome.replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                )
                stmt = stmt.where(
                    ProdutoModel.nome.like(f"%{escaped_nome}%", escape="\\")
                )

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

            produtos = session.scalars(stmt).all()
            return produtos

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a consulta.",
        )