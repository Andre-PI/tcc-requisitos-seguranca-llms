import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, Session, sessionmaker

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_url = f"sqlite:///{db_path}"
else:
    db_url = db_path

engine = create_engine(db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class ProdutoDB(Base):
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
    stmt = select(ProdutoDB)

    if nome is not None:
        stmt = stmt.where(ProdutoDB.nome.contains(nome))
    if categoria is not None:
        stmt = stmt.where(ProdutoDB.categoria == categoria)
    if preco_min is not None:
        stmt = stmt.where(ProdutoDB.preco >= preco_min)
    if preco_max is not None:
        stmt = stmt.where(ProdutoDB.preco <= preco_max)

    if ordenar_por == "preco":
        stmt = stmt.order_by(ProdutoDB.preco.asc())
    elif ordenar_por == "nome":
        stmt = stmt.order_by(ProdutoDB.nome.asc())

    produtos = db.scalars(stmt).all()
    return produtos