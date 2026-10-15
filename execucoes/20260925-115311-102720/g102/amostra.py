from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from datetime import datetime
from decimal import Decimal

router = APIRouter()

# Assumindo que estes objetos já existem na aplicação:
# - get_db: dependency que fornece a sessão/conexão com o banco
# - get_current_user: dependency que retorna o usuário autenticado
# - Pedido, ItemPedido: modelos ORM/SQLAlchemy
from app.database import get_db
from app.auth import get_current_user
from app.models import Pedido, ItemPedido


class ItemPedidoResponse(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: Decimal


class PedidoResponse(BaseModel):
    numero: str
    data: datetime
    status: str
    valor_total: Decimal
    itens: List[ItemPedidoResponse]


@router.get("/pedidos/{id}", response_model=PedidoResponse)
def obter_pedido(id: int, db=Depends(get_db), usuario=Depends(get_current_user)):
    pedido = (
        db.query(Pedido)
        .filter(Pedido.id == id, Pedido.usuario_id == usuario.id)
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

    return PedidoResponse(
        numero=pedido.numero,
        data=pedido.data,
        status=pedido.status,
        valor_total=pedido.valor_total,
        itens=[
            ItemPedidoResponse(
                produto_nome=item.produto_nome,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
            )
            for item in itens
        ],
    )