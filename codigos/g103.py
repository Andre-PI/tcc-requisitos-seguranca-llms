from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from datetime import date, datetime
from sqlalchemy.orm import Session

router = APIRouter()


class ItemPedidoOut(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoOut(BaseModel):
    numero: str
    data: date | datetime
    status: str
    valor_total: float
    itens: List[ItemPedidoOut]


# Dependências esperadas na aplicação
def get_db() -> Session:
    raise NotImplementedError


def get_current_user():
    raise NotImplementedError


# Modelos ORM esperados na aplicação
class Pedido:
    id: int
    usuario_id: int
    numero: str
    data: date | datetime
    valor_total: float
    status: str


class ItemPedido:
    pedido_id: int
    produto_nome: str
    quantidade: int
    preco_unitario: float


@router.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(id: int, db: Session = Depends(get_db), usuario = Depends(get_current_user)):
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