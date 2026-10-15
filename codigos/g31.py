from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from datetime import date
from typing import List
from pydantic import BaseModel
from app.dependencies import get_db, get_current_user
from app.models import Pedido, ItemPedido, Usuario

router = APIRouter()

class ItemResponse(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float

class PedidoResponse(BaseModel):
    numero: str
    data: date
    status: str
    valor_total: float
    itens: List[ItemResponse]

@router.get("/pedidos/{id}", response_model=PedidoResponse)
def get_pedido(id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
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
        itens=[
            ItemResponse(
                produto_nome=item.produto_nome,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
            )
            for item in pedido.itens
        ],
    )