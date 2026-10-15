from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import date

app = FastAPI()

# Supondo que já existam as funções e dependências para obter o DB e o usuário autenticado:
def get_db():
    # retorna uma sessão do banco
    pass

def get_current_user():
    # retorna o usuário autenticado
    pass

# Models SQLAlchemy (simplificados)
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer)
    numero = Column(String)
    data = Column(Date)
    valor_total = Column(Float)
    status = Column(String)
    itens = relationship("ItemPedido", back_populates="pedido")

class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    produto_nome = Column(String)
    quantidade = Column(Integer)
    preco_unitario = Column(Float)
    pedido = relationship("Pedido", back_populates="itens")

# Schemas Pydantic
class ItemPedidoResponse(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float

    class Config:
        orm_mode = True

class PedidoResponse(BaseModel):
    numero: str
    data: date
    status: str
    valor_total: float
    itens: List[ItemPedidoResponse]

    class Config:
        orm_mode = True

@app.get("/pedidos/{id}", response_model=PedidoResponse)
def get_pedido(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    pedido = db.query(Pedido).filter(Pedido.id == id, Pedido.usuario_id == current_user.id).first()
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    return pedido