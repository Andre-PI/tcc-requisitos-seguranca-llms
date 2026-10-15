from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ajuste estes imports conforme a estrutura da sua aplicação
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models import Pedido, ItemPedido, Usuario


router = APIRouter(prefix="/pedidos", tags=["pedidos"])


class ItemPedidoResponse(BaseModel):
    produto_nome: str = Field(..., max_length=255)
    quantidade: int = Field(..., ge=1)
    preco_unitario: Decimal


class PedidoResponse(BaseModel):
    numero: str = Field(..., max_length=100)
    data: date
    status: str = Field(..., max_length=50)
    valor_total: Decimal
    itens: List[ItemPedidoResponse]


@router.get("/{id}", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
async def obter_pedido(
    id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PedidoResponse:
    if id <= 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    stmt = (
        select(Pedido)
        .where(Pedido.id == id)
        .where(Pedido.usuario_id == current_user.id)
    )
    result = await db.execute(stmt)
    pedido: Optional[Pedido] = result.scalar_one_or_none()

    if pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    itens_stmt = (
        select(ItemPedido)
        .where(ItemPedido.pedido_id == pedido.id)
        .order_by(ItemPedido.produto_nome.asc())
    )
    itens_result = await db.execute(itens_stmt)
    itens = itens_result.scalars().all()

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