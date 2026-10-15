from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from typing import List
from decimal import Decimal
from datetime import datetime

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


class PedidoItemResponse(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: Decimal

    model_config = ConfigDict(from_attributes=True)


class PedidoResponse(BaseModel):
    numero: str
    data: datetime
    status: str
    valor_total: Decimal
    itens: List[PedidoItemResponse]

    model_config = ConfigDict(from_attributes=True)


# Dependências esperadas na aplicação:
# - get_db: fornece a sessão do banco
# - get_current_user: retorna o usuário autenticado
# - models.Pedido e models.ItemPedido: modelos ORM
from app.dependencies import get_db, get_current_user
from app.models import Pedido, ItemPedido


@router.get(
    "/{id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Pedido não encontrado"}},
)
def obter_pedido(
    id: int,
    db=Depends(get_db),
    usuario=Depends(get_current_user),
):
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
            PedidoItemResponse(
                produto_nome=item.produto_nome,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
            )
            for item in itens
        ],
    )