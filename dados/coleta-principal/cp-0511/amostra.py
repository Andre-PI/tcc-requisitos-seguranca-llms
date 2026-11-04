import os
from typing import Annotated, List, Literal, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

db_path = os.getenv("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    database_url = f"sqlite:///{db_path}"
else:
    database_url = db_path

engine = create_engine(database_url, connect_args={"check_same_thread": False})
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
    nome: Annotated[Optional[str], Query(max_length=100)] = None,
    categoria: Annotated[Optional[str], Query(max_length=100)] = None,
    preco_min: Annotated[Optional[float], Query(ge=0.0)] = None,
    preco_max: Annotated[Optional[float], Query(ge=0.0)] = None,
    ordenar_por: Annotated[Optional[Literal["preco", "nome"]], Query()] = None,
):
    with SessionLocal() as db:
        stmt = select(ProdutoModel)

        if nome:
            escaped_nome = (
                nome.replace("/", "//").replace("%", "/%").replace("_", "/_")
            )
            stmt = stmt.where(
                ProdutoModel.nome.ilike(f"%{escaped_nome}%", escape="/")
            )

        if categoria:
            stmt = stmt.where(ProdutoModel.categoria == categoria)

        if preco_min is not None:
            stmt = stmt.where(ProdutoModel.preco >= preco_min)

        if preco_max is not None:
            stmt = stmt.where(ProdutoModel.preco <= preco_max)

        if ordenar_por == "preco":
            stmt = stmt.order_by(ProdutoModel.preco.asc())
        elif ordenar_por == "nome":
            stmt = stmt.order_by(ProdutoModel.nome.asc())

        results = db.scalars(stmt).all()
        return results