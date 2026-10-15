from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional, Any

router = APIRouter()


class ItemPedidoResponse(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoResponse(BaseModel):
    numero: str
    data: Any
    status: str
    valor_total: float
    itens: List[ItemPedidoResponse]


# Ajuste estes imports/Depends conforme a sua aplicação
# from app.auth import get_current_user
# from app.db import get_db

def get_current_user():
    raise NotImplementedError


def get_db():
    raise NotImplementedError


@router.get("/pedidos/{id}", response_model=PedidoResponse)
def obter_pedido(id: int, usuario_autenticado=Depends(get_current_user), db=Depends(get_db)):
    pedido = db.execute(
        """
        SELECT id, usuario_id, numero, data, valor_total, status
        FROM pedidos
        WHERE id = :id AND usuario_id = :usuario_id
        """,
        {"id": id, "usuario_id": usuario_autenticado.id},
    ).fetchone()

    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    itens = db.execute(
        """
        SELECT produto_nome, quantidade, preco_unitario
        FROM itens_pedido
        WHERE pedido_id = :pedido_id
        """,
        {"pedido_id": id},
    ).fetchall()

    return PedidoResponse(
        numero=pedido["numero"] if isinstance(pedido, dict) else pedido.numero,
        data=pedido["data"] if isinstance(pedido, dict) else pedido.data,
        status=pedido["status"] if isinstance(pedido, dict) else pedido.status,
        valor_total=pedido["valor_total"] if isinstance(pedido, dict) else pedido.valor_total,
        itens=[
            ItemPedidoResponse(
                produto_nome=item["produto_nome"] if isinstance(item, dict) else item.produto_nome,
                quantidade=item["quantidade"] if isinstance(item, dict) else item.quantidade,
                preco_unitario=item["preco_unitario"] if isinstance(item, dict) else item.preco_unitario,
            )
            for item in itens
        ],
    )