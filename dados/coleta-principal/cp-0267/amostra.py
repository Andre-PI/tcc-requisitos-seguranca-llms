import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, select, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session, Mapped, mapped_column
from tcc_t06_infra import usuario_atual

db_path = os.environ.get("TCC_DB_PATH", "banco.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PedidoDB(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column()
    numero: Mapped[str] = mapped_column()
    data: Mapped[str] = mapped_column()
    valor_total: Mapped[float] = mapped_column()
    status: Mapped[str] = mapped_column()

    itens: Mapped[List["ItemPedidoDB"]] = relationship(back_populates="pedido")


class ItemPedidoDB(Base):
    __tablename__ = "itens_pedido"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    produto_nome: Mapped[str] = mapped_column()
    quantidade: Mapped[int] = mapped_column()
    preco_unitario: Mapped[float] = mapped_column()

    pedido: Mapped["PedidoDB"] = relationship(back_populates="itens")


class ItemResponse(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float

    model_config = {"from_attributes": True}


class PedidoResponse(BaseModel):
    numero: str
    data: str
    status: str
    valor_total: float
    itens: List[ItemResponse]

    model_config = {"from_attributes": True}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()


@app.get("/pedidos/{id}", response_model=PedidoResponse)
def get_pedido(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(usuario_atual),
):
    stmt = (
        select(PedidoDB)
        .where(PedidoDB.id == id, PedidoDB.usuario_id == current_user["id"])
    )
    pedido = db.execute(stmt).scalars().first()

    if pedido is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado",
        )

    return pedido