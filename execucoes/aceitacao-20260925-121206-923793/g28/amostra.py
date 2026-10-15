from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import List
from datetime import date
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Supondo que você já tenha a configuração do banco e as models SQLAlchemy:

from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from database import SessionLocal  # SessionLocal do SQLAlchemy configurado previamente

Base = declarative_base()

class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, index=True)
    numero = Column(String, unique=True, index=True)
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

# Pydantic schemas

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

# Dependência para obter o usuário autenticado
def get_current_user(token: str = Depends(oauth2_scheme)):
    # Aqui deve ser implementada a lógica para obter o usuário a partir do token
    # Exemplo fictício:
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    return user

def fake_decode_token(token: str):
    # Função fictícia que retorna um usuário com id 1 para qualquer token válido
    class User:
        id = 1
    if token:
        return User()
    return None

# Dependência para obter a sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/pedidos/{id}", response_model=PedidoResponse)
def get_pedido(id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    pedido = db.query(Pedido).options(joinedload(Pedido.itens)).filter(Pedido.id == id, Pedido.usuario_id == current_user.id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido