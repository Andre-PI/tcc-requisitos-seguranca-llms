import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, select, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship, Mapped, mapped_column
from tcc_t06_infra import usuario_atual

db_path = os.environ.get("TCC_DB_PATH", "database.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PedidoModel(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(nullable=False)
    numero: Mapped[str] = mapped_column(nullable=False)
    data: Mapped[str] = mapped_column(nullable=False)
    valor_total: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)

    itens = relationship("ItemPedidoModel", back_populates="pedido")


class ItemPedidoModel(Base):
    __tablename__ = "itens_pedido"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), nullable=False)
    produto_nome: Mapped[str] = mapped_column(nullable=False)
    quantidade: Mapped[int] = mapped_column(nullable=False)
    preco_unitario: Mapped[float] = mapped_column(nullable=False)

    pedido = relationship("PedidoModel", back_populates="itens")


class ItemPedidoResponse(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float

    class Config:
        from_attributes = True


class PedidoResponse(BaseModel):
    numero: str
    data: str
    status: str
    valor_total: float
    itens: List[ItemPedidoResponse]

    class Config:
        from_attributes = True


app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/pedidos/{id}", response_model=PedidoResponse)
def obter_pedido(
    id: int,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual)
):
    stmt = (
        select(PedidoModel)
        .where(PedidoModel.id == id, PedidoModel.usuario_id == usuario["id"])
    )
    pedido = db.execute(stmt).scalars().first()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado"
        )

    return pedido