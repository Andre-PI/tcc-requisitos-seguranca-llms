import os
from typing import Generator, List, Optional
from fastapi import FastAPI, Depends, Query, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, Float, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session

db_path = os.getenv("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_path = f"sqlite:///{db_path}"

engine = create_engine(
    db_path,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProdutoDB(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    preco = Column(Float, nullable=False)
    estoque = Column(Integer, nullable=False)


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


def escape_like_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@app.get("/produtos", response_model=List[ProdutoResponse], status_code=status.HTTP_200_OK)
def buscar_produtos(
    nome: Optional[str] = Query(None, max_length=100),
    categoria: Optional[str] = Query(None, max_length=100),
    preco_min: Optional[float] = Query(None, ge=0.0),
    preco_max: Optional[float] = Query(None, ge=0.0),
    ordenar_por: Optional[str] = Query(None, pattern="^(preco|nome)$"),
    db: Session = Depends(get_db)
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preco_min nao pode ser maior que preco_max."
        )

    stmt = select(ProdutoDB)

    if nome:
        escaped_nome = escape_like_string(nome)
        stmt = stmt.where(ProdutoDB.nome.ilike(f"%{escaped_nome}%", escape="\\"))

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