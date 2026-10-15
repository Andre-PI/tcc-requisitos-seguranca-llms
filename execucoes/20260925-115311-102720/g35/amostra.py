from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List
from datetime import date
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base

# Configurações do banco (exemplo)
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Models SQLAlchemy
class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, index=True)
    numero = Column(String, nullable=False)
    data = Column(Date, nullable=False)
    valor_total = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    itens = relationship("ItemPedido", back_populates="pedido")

class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    produto_nome = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)
    pedido = relationship("Pedido", back_populates="itens")

# Pydantic schemas
class ItemResponse(BaseModel):
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
    itens: List[ItemResponse]

# Simulação do sistema de autenticação por token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Função stub para extrair usuário autenticado do token
def get_usuario_id_do_token(token: str = Depends(oauth2_scheme)) -> int:
    # Aqui você implementaria a lógica real para extrair o usuário do token
    # Para exemplo, vamos supor que o token é simplesmente o id do usuário como string
    try:
        return int(token)
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

app = FastAPI()

# Dependency para obter sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/pedidos/{id}", response_model=PedidoResponse)
def obter_pedido(id: int, usuario_id: int = Depends(get_usuario_id_do_token), db: Session = Depends(get_db)):
    pedido = db.query(Pedido).filter(Pedido.id == id).first()
    if not pedido or pedido.usuario_id != usuario_id:
        # Retorna 404 tanto se não existir quanto se pertencer a outro usuário
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    return PedidoResponse(
        numero=pedido.numero,
        data=pedido.data,
        status=pedido.status,
        valor_total=pedido.valor_total,
        itens=pedido.itens
    )