import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, select, Float, Integer, String
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, Session, sessionmaker

db_path = os.getenv("TCC_DB_PATH", "produtos.db")
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProdutoModel(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String)
    categoria: Mapped[str] = mapped_column(String)
    preco: Mapped[float] = mapped_column(Float)
    estoque: Mapped[int] = mapped_column(Integer)


class ProdutoSchema(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    model_config = ConfigDict(from_attributes=True)


app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@app.get("/produtos", response_model=List[ProdutoSchema])
def listar_produtos(
    nome: Optional[str] = Query(None, max_length=100),
    categoria: Optional[str] = Query(None, max_length=100),
    preco_min: Optional[float] = Query(None, ge=0.0),
    preco_max: Optional[float] = Query(None, ge=0.0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
    db: Session = Depends(get_db),
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(
            status_code=400,
            detail="preco_min nao pode ser maior que preco_max",
        )

    query = select(ProdutoModel)

    if nome:
        escaped_nome = escape_like(nome)
        query = query.where(ProdutoModel.nome.like(f"%{escaped_nome}%", escape="\\"))

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