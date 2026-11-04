import os
from typing import Generator, List, Literal, Optional
from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, select, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "produtos.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String)
    categoria: Mapped[str] = mapped_column(String)
    preco: Mapped[float] = mapped_column(Float)
    estoque: Mapped[int] = mapped_column(Integer)


class ProdutoResponse(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    model_config = ConfigDict(from_attributes=True)


app = FastAPI()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def escape_like_pattern(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@app.get("/produtos", response_model=List[ProdutoResponse])
def listar_produtos(
    nome: Optional[str] = Query(None, max_length=100),
    categoria: Optional[str] = Query(None, max_length=50),
    preco_min: Optional[float] = Query(None, ge=0.0),
    preco_max: Optional[float] = Query(None, ge=0.0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
    db: Session = Depends(get_db)
):
    query = select(Produto)

    if nome:
        escaped_nome = escape_like_pattern(nome)
        query = query.where(Produto.nome.ilike(f"%{escaped_nome}%", escape="\\"))

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

    produtos = db.scalars(query).all()
    return produtos