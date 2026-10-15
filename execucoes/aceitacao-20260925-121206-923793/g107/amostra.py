from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from datetime import date, datetime
from decimal import Decimal

router = APIRouter()


# Ajuste estes imports/dependencies conforme a sua aplicação
# from app.auth import get_current_user
# from app.db import get_db
#
# get_current_user deve retornar o usuário autenticado a partir do token
# get_db deve fornecer uma sessão/conexão com o banco


class ItemPedidoOut(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: Decimal


class PedidoOut(BaseModel):
    numero: str
    data: date | datetime
    status: str
    valor_total: Decimal
    itens: List[ItemPedidoOut]


@router.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(
    id: int,
    current_user=Depends(...),  # substitua por Depends(get_current_user)
    db=Depends(...),            # substitua por Depends(get_db)
):
    usuario_id = getattr(current_user, "id", None)
    if usuario_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    pedido = db.execute(
        """
        SELECT id, usuario_id, numero, data, valor_total, status
        FROM pedidos
        WHERE id = :id
        """,
        {"id": id},
    ).fetchone()

    if not pedido or pedido["usuario_id"] != usuario_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    itens = db.execute(
        """
        SELECT produto_nome, quantidade, preco_unitario
        FROM itens_pedido
        WHERE pedido_id = :pedido_id
        ORDER BY produto_nome
        """,
        {"pedido_id": id},
    ).fetchall()

    return {
        "numero": pedido["numero"],
        "data": pedido["data"],
        "status": pedido["status"],
        "valor_total": pedido["valor_total"],
        "itens": [
            {
                "produto_nome": item["produto_nome"],
                "quantidade": item["quantidade"],
                "preco_unitario": item["preco_unitario"],
            }
            for item in itens
        ],
    }