from fastapi import FastAPI, Query
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Optional, List

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    categoria = Column(String, index=True)
    preco = Column(Float, index=True)
    estoque = Column(Integer)

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/produtos")
def listar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[str] = Query(None, pattern="^(preco|nome)$"),
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

        produtos = query.all()

        return [
            {
                "id": p.id,
                "nome": p.nome,
                "categoria": p.categoria,
                "preco": p.preco,
                "estoque": p.estoque,
            }
            for p in produtos
        ]
    finally:
        db.close()