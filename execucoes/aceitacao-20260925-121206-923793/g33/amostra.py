from fastapi import FastAPI, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import List
from datetime import date
from app.database import get_db
from app.models import Pedido, ItemPedido
from app.auth import get_current_user, User

app = FastAPI()

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

    class Config:
        orm_mode = True

@app.get("/pedidos/{id}", response_model=PedidoResponse)
def get_pedido(
    id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pedido = (
        db.query(Pedido)
        .options(joinedload(Pedido.itens))
        .filter(Pedido.id == id, Pedido.usuario_id == current_user.id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    return PedidoResponse(
        numero=pedido.numero,
        data=pedido.data,
        status=pedido.status,
        valor_total=pedido.valor_total,
        itens=pedido.itens
    )