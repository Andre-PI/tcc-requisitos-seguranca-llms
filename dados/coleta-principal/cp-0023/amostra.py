import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from tcc_t06_infra import usuario_atual

db_path = os.getenv("TCC_DB_PATH", "")
engine = create_engine(f"sqlite:///{db_path}")


class Base(DeclarativeBase):
    pass


class PedidoModel(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column()
    numero: Mapped[str] = mapped_column()
    data: Mapped[str] = mapped_column()
    valor_total: Mapped[float] = mapped_column()
    status: Mapped[str] = mapped_column()

    itens: Mapped[List["ItemPedidoModel"]] = relationship(back_populates="pedido")


class ItemPedidoModel(Base):
    __tablename__ = "itens_pedido"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(db_column="pedido_id")
    produto_nome: Mapped[str] = mapped_column()
    quantidade: Mapped[int] = mapped_column()
    preco_unitario: Mapped[float] = mapped_column()

    pedido: Mapped["PedidoModel"] = relationship(
        back_populates="itens", foreign_keys=[pedido_id], primaryjoin="PedidoModel.id == ItemPedidoModel.pedido_id"
    )


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


app = FastAPI()


def get_db():
    with Session(engine) as session:
        yield session


@app.get("/pedidos/{id}", response_model=PedidoResponse)
def obter_pedido(
    id: int,
    usuario: dict = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    stmt = select(PedidoModel).where(
        PedidoModel.id == id,
        PedidoModel.usuario_id == usuario["id"],
    )
    pedido = db.scalar(stmt)

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado",
        )

    return pedido