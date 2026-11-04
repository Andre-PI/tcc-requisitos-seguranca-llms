import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, select, Float, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session, Mapped, mapped_column

db_path = os.getenv("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_url = f"sqlite:///{db_path}"
else:
    db_url = db_path

engine = create_engine(db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProdutoDB(Base):
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

    if nome:
        stmt = stmt.where(ProdutoDB.nome.ilike(f"%{nome}%"))
    if categoria:
        stmt = stmt.where(ProdutoDB.categoria == categoria)
    if preco_min is not None:
        stmt = stmt.where(ProdutoDB.preco >= preco_min)
    if preco_max is not None:
        stmt = stmt.where(ProdutoDB.preco <= preco_max)

    if ordenar_por == "preco":
        stmt = stmt.order_by(ProdutoDB.preco.asc())
    elif ordenar_por == "nome":
        stmt = stmt.order_by(ProdutoDB.nome.asc())

    resultados = db.execute(stmt).scalars().all()
    return resultados