import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from tcc_t06_infra import usuario_atual

db_path = os.getenv("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_path = f"sqlite:///{db_path}"

engine = create_engine(db_path, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PedidoDB(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer)
    numero = Column(String)
    data = Column(String)
    valor_total = Column(Float)
    status = Column(String)

    itens = relationship("ItemPedidoDB", back_populates="pedido")


class ItemPedidoDB(Base):
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True)
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()


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