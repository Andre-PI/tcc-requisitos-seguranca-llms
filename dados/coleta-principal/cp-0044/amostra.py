import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, select, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship, Mapped, mapped_column
from tcc_t06_infra import usuario_atual

db_path = os.environ.get("TCC_DB_PATH", "sqlite:///./test.db")
if not db_path.startswith("sqlite:///"):
    db_path = f"sqlite:///{db_path}"

engine = create_engine(db_path, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column()
    numero: Mapped[str] = mapped_column()
    data: Mapped[str] = mapped_column()
    valor_total: Mapped[float] = mapped_column()
    status: Mapped[str] = mapped_column()

    itens: Mapped[List["ItemPedido"]] = relationship(back_populates="pedido")

class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    produto_nome: Mapped[str] = mapped_column()
    quantidade: Mapped[int] = mapped_column()
    preco_unitario: Mapped[float] = mapped_column()

    pedido: Mapped["Pedido"] = relationship(back_populates="itens")

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
    usuario: dict = Depends(usuario_atual)
):
    stmt = select(Pedido).where(Pedido.id == id, Pedido.usuario_id == usuario["id"])
    pedido = db.execute(stmt).scalars().first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado"
        )
    return pedido