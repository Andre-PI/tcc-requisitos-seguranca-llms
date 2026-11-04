import os
from typing import List, Literal, Optional
from fastapi import FastAPI, Query, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

db_path = os.getenv("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_path = f"sqlite:///{db_path}"

engine = create_engine(db_path, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

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
def listar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
    db: Session = Depends(get_db)
):
    stmt = select(ProdutoModel)

    if nome:
        stmt = stmt.where(ProdutoModel.nome.contains(nome))
    if categoria:
        stmt = stmt.where(ProdutoModel.categoria == categoria)
    if preco_min is not None:
        stmt = stmt.where(ProdutoModel.preco >= preco_min)
    if preco_max is not None:
        stmt = stmt.where(ProdutoModel.preco <= preco_max)

    if ordenar_por == "preco":
        stmt = stmt.order_by(ProdutoModel.preco.asc())
    elif ordenar_por == "nome":
        stmt = stmt.order_by(ProdutoModel.nome.asc())

    resultados = db.scalars(stmt).all()
    return resultados