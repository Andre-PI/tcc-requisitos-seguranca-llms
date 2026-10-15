from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, relationship, joinedload
from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from typing import List
from pydantic import BaseModel
from datetime import date

# Configurações básicas do SQLAlchemy (exemplo)
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Models SQLAlchemy
class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, index=True)
    numero = Column(String, index=True)
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

# Função simulada para obter usuário autenticado a partir do token
def get_usuario_id(token: str = Depends(oauth2_scheme)) -> int:
    # Aqui você deve validar o token e retornar o usuario_id correspondente
    # Exemplo fictício, substitua pela lógica real
    if token == "token_usuario_1":
        return 1
    elif token == "token_usuario_2":
        return 2
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

# Dependência para obter sessão do DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/pedidos/{id}", response_model=PedidoResponse)
def get_pedido(id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    pedido = (
        db.query(Pedido)
        .options(joinedload(Pedido.itens))
        .filter(Pedido.id == id, Pedido.usuario_id == usuario_id)
        .first()
    )
    if not pedido:
        # Retorna 404 se pedido não existir ou não pertencer ao usuário autenticado
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    return PedidoResponse(
        numero=pedido.numero,
        data=pedido.data,
        status=pedido.status,
        valor_total=pedido.valor_total,
        itens=pedido.itens
    )