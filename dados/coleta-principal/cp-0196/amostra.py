import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy import Column, Integer, String, Float, ForeignKey

from tcc_t06_infra import usuario_atual

DB_PATH = os.environ.get("TCC_DB_PATH", "sqlite:///./database.db")
if not DB_PATH.startswith("sqlite:///"):
    DB_URI = f"sqlite:///{DB_PATH}"
else:
    DB_URI = DB_PATH

engine = create_engine(DB_URI, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PedidoModel(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=False)
    numero = Column(String, nullable=False)
    data = Column(String, nullable=False)
    valor_total = Column(Float, nullable=False)
    status = Column(String, nullable=False)

    itens = relationship("ItemPedidoModel", back_populates="pedido")


class ItemPedidoModel(Base):
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    produto_nome = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)

    pedido = relationship("PedidoModel", back_populates="itens")


class ItemResponse(BaseModel):
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
    itens: List[ItemResponse]

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
    usuario: dict = Depends(usuario_atual),
):
    stmt = (
        select(PedidoModel)
        .where(PedidoModel.id == id, PedidoModel.usuario_id == usuario["id"])
    )
    pedido = db.execute(stmt).scalars().first()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado",
        )

    return pedido