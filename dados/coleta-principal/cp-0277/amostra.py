import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session, Mapped, mapped_column

DB_PATH = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not DB_PATH.startswith("sqlite:///"):
    DATABASE_URL = f"sqlite:///{DB_PATH}"
else:
    DATABASE_URL = DB_PATH

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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

    class Config:
        from_attributes = True


app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/produtos", response_model=List[ProdutoResponse])
def get_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(ProdutoModel)

    if nome:
        query = query.where(ProdutoModel.nome.like(f"%{nome}%"))
    if categoria:
        query = query.where(ProdutoModel.categoria == categoria)
    if preco_min is not None:
        query = query.where(ProdutoModel.preco >= preco_min)
    if preco_max is not None:
        query = query.where(ProdutoModel.preco <= preco_max)

    if ordenar_por == "preco":
        query = query.order_by(ProdutoModel.preco.asc())
    elif ordenar_por == "nome":
        query = query.order_by(ProdutoModel.nome.asc())

    resultados = db.scalars(query).all()
    return resultados