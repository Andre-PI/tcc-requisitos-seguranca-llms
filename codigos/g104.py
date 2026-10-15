from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import date, datetime
from decimal import Decimal

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    produto_nome: str
    quantidade: int
    preco_unitario: Decimal


class PedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero: str
    data: date | datetime
    status: str
    valor_total: Decimal
    itens: List[ItemPedidoOut]


# Assumptions:
# - A dependency get_db() returns a SQLAlchemy Session
# - A dependency get_current_user() returns the authenticated user object with attribute id
# - ORM models Pedido and ItemPedido exist and are mapped to the tables pedidos and itens_pedido
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models import Pedido, ItemPedido


@router.get("/{id}", response_model=PedidoOut, status_code=status.HTTP_200_OK)
def obter_pedido(
    id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    pedido = (
        db.query(Pedido)
        .filter(Pedido.id == id, Pedido.usuario_id == current_user.id)
        .first()
    )

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado",
        )

    itens = (
        db.query(ItemPedido)
        .filter(ItemPedido.pedido_id == pedido.id)
        .all()
    )

    return PedidoOut(
        numero=pedido.numero,
        data=pedido.data,
        status=pedido.status,
        valor_total=pedido.valor_total,
        itens=[
            ItemPedidoOut(
                produto_nome=item.produto_nome,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
            )
            for item in itens
        ],
    )