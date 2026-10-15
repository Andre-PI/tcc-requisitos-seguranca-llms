from fastapi import FastAPI, Query
from typing import Optional, List, Literal
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = "sqlite:///./produtos.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI()


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True, nullable=False)
    categoria = Column(String, index=True, nullable=False)
    preco = Column(Float, nullable=False)
    estoque = Column(Integer, nullable=False)


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    class Config:
        from_attributes = True


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/produtos", response_model=List[ProdutoOut])
def buscar_produtos(
    nome: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    preco_min: Optional[float] = Query(default=None),
    preco_max: Optional[float] = Query(default=None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    db: Session = SessionLocal()
    try:
        query = db.query(Produto)

        if nome is not None:
            query = query.filter(Produto.nome.ilike(f"%{nome}%"))
        if categoria is not None:
            query = query.filter(Produto.categoria == categoria)
        if preco_min is not None:
            query = query.filter(Produto.preco >= preco_min)
        if preco_max is not None:
            query = query.filter(Produto.preco <= preco_max)

        if ordenar_por == "preco":
            query = query.order_by(Produto.preco)
        elif ordenar_por == "nome":
            query = query.order_by(Produto.nome)

        return query.all()
    finally:
        db.close()