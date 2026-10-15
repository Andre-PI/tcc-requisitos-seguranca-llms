from typing import Annotated, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy import Numeric, String, and_, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.sql import func

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    categoria: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    preco: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, index=True)
    estoque: Mapped[int] = mapped_column(nullable=False)


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


class ProdutoQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: Optional[str] = Field(default=None, max_length=255)
    categoria: Optional[str] = Field(default=None, max_length=120)
    preco_min: Optional[float] = Field(default=None, ge=0)
    preco_max: Optional[float] = Field(default=None, ge=0)
    ordenar_por: Optional[Literal["preco", "nome"]] = None

    @field_validator("nome", "categoria")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("preco_max")
    @classmethod
    def validate_price_range(cls, v: Optional[float], info):
        preco_min = info.data.get("preco_min")
        if v is not None and preco_min is not None and v < preco_min:
            raise ValueError("preco_max deve ser maior ou igual a preco_min")
        return v


app = FastAPI(title="API de Produtos")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None, max_length=255)] = None,
    categoria: Annotated[Optional[str], Query(default=None, max_length=120)] = None,
    preco_min: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    preco_max: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    ordenar_por: Annotated[Optional[Literal["preco", "nome"]], Query(default=None)] = None,
):
    try:
        query_params = ProdutoQuery(
            nome=nome,
            categoria=categoria,
            preco_min=preco_min,
            preco_max=preco_max,
            ordenar_por=ordenar_por,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    conditions = []
    if query_params.nome:
        conditions.append(func.lower(Produto.nome).like(f"%{query_params.nome.lower()}%"))
    if query_params.categoria:
        conditions.append(func.lower(Produto.categoria) == query_params.categoria.lower())
    if query_params.preco_min is not None:
        conditions.append(Produto.preco >= query_params.preco_min)
    if query_params.preco_max is not None:
        conditions.append(Produto.preco <= query_params.preco_max)

    stmt = select(Produto)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    if query_params.ordenar_por == "preco":
        stmt = stmt.order_by(Produto.preco.asc(), Produto.nome.asc())
    elif query_params.ordenar_por == "nome":
        stmt = stmt.order_by(Produto.nome.asc(), Produto.id.asc())

    try:
        with SessionLocal() as session:
            produtos = session.scalars(stmt).all()
            return produtos
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro ao consultar produtos")