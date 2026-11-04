import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

db_path = os.getenv("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///") and not db_path.startswith("sqlite:////"):
    db_url = f"sqlite:///{db_path}"
else:
    db_url = db_path

engine = create_engine(db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column()
    categoria: Mapped[str] = mapped_column()
    preco: Mapped[float] = mapped_column()
    estoque: Mapped[int] = mapped_column()


class ProdutoOut(BaseModel):
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


@app.get("/produtos", response_model=List[ProdutoOut])
def listar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(Produto)

    if nome:
        query = query.where(Produto.nome.like(f"%{nome}%"))
    if categoria:
        query = query.where(Produto.categoria == categoria)
    if preco_min is not None:
        query = query.where(Produto.preco >= preco_min)
    if preco_max is not None:
        query = query.where(Produto.preco <= preco_max)

    if ordenar_por == "preco":
        query = query.order_by(Produto.preco.asc())
    elif ordenar_por == "nome":
        query = query.order_by(Produto.nome.asc())

    resultados = db.scalars(query).all()
    return resultados