import os
from typing import Generator, List, Literal, Optional
from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

db_path = os.getenv("TCC_DB_PATH", "database.db")
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ProdutoModel(Base):
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


@app.get("/produtos", response_model=List[ProdutoResponse])
def listar_produtos(
    nome: Optional[str] = Query(None, max_length=100),
    categoria: Optional[str] = Query(None, max_length=100),
    preco_min: Optional[float] = Query(None, ge=0),
    preco_max: Optional[float] = Query(None, ge=0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(ProdutoModel)

    if nome:
        escaped_nome = (
            nome.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        query = query.where(ProdutoModel.nome.ilike(f"%{escaped_nome}%", escape="\\"))

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

    produtos = db.scalars(query).all()
    return produtos