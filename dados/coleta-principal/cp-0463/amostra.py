import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, ForeignKey, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from tcc_t06_infra import usuario_atual

DB_PATH = os.environ.get("TCC_DB_PATH", "sqlite:///tcc.db")
if not DB_PATH.startswith("sqlite:///"):
    DB_PATH = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PedidoDB(Base):
    __tablename__ = "pedidos"

    id = Column = Integer
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer)
    numero = Column(String)
    data = Column(String)
    valor_total = Column(Float)
    status = Column(String)

    itens = relationship("ItemPedidoDB", back_populates="pedido")


class ItemPedidoDB(Base):
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    produto_nome = Column(String)
    quantidade = Column(Integer)
    preco_unitario = Column(Float)

    pedido = relationship("PedidoDB", back_populates="itens")


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
    pedido = (
        db.query(PedidoDB)
        .filter(PedidoDB.id == id, PedidoDB.usuario_id == usuario["id"])
        .first()
    )
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado",
        )
    return pedido