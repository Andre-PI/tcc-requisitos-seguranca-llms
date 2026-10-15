from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Any

router = APIRouter()


class ItemPedidoOut(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoOut(BaseModel):
    numero: str
    data: Any
    status: str
    valor_total: float
    itens: List[ItemPedidoOut]


# Dependências esperadas na aplicação:
# - get_current_user: retorna o usuário autenticado a partir do token
# - get_db: retorna uma sessão/conexão com o banco
#
# Ajuste os imports/implementações conforme a estrutura do seu projeto.
from app.auth import get_current_user
from app.db import get_db


@router.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(
    id: int,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    pedido = db.execute(
        """
        SELECT id, usuario_id, numero, data, valor_total, status
        FROM pedidos
        WHERE id = :id
        """,
        {"id": id},
    ).fetchone()

    if pedido is None or pedido["usuario_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado",
        )

    itens = db.execute(
        """
        SELECT produto_nome, quantidade, preco_unitario
        FROM itens_pedido
        WHERE pedido_id = :pedido_id
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