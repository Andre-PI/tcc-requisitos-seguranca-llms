import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, select, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session

db_path = os.getenv("TCC_DB_PATH", "database.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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
    nome: Optional[str] = Query(None, max_length=100),
    categoria: Optional[str] = Query(None, max_length=100),
    preco_min: Optional[float] = Query(None, ge=0.0),
    preco_max: Optional[float] = Query(None, ge=0.0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preco_min nao pode ser maior que preco_max"
        )

    db: Session = SessionLocal()
    try:
        stmt = select(ProdutoModel)

        if nome:
            sanitized_nome = nome.replace("/", "//").replace("%", "/%").replace("_", "/_")
            stmt = stmt.where(ProdutoModel.nome.ilike(f"%{sanitized_nome}%", escape="/"))

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

        results = db.execute(stmt).scalars().all()
        return results
    finally:
        db.close()