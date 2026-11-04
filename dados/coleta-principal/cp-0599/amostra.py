import os
from typing import List, Literal, Optional
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, Numeric, String, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_path = f"sqlite:///{db_path}"

engine = create_engine(db_path, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True)
    nome = Column(String)
    categoria = Column(String)
    preco = Column(Numeric)
    estoque = Column(Integer)


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    model_config = ConfigDict(from_attributes=True)


app = FastAPI()


@app.get("/produtos", response_model=List[ProdutoOut])
def listar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None, ge=0),
    preco_max: Optional[float] = Query(None, ge=0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="preco_min nao pode ser maior que preco_max",
        )

    stmt = select(Produto)

    if nome:
        escaped_nome = nome.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Produto.nome.like(f"%{escaped_nome}%", escape="\\"))
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

    try:
        with SessionLocal() as session:
            resultados = session.scalars(stmt).all()
            return resultados
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a solicitacao.",
        )