import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import declarative_base, Session, sessionmaker, Mapped, mapped_column

db_path = os.getenv("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_url = f"sqlite:///{db_path}"
else:
    db_url = db_path

engine = create_engine(db_url, connect_args={"check_same_thread": False})
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

    if nome is not None:
        query = query.where(ProdutoModel.nome.ilike(f"%{nome}%"))
    if categoria is not None:
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