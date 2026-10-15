from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from datetime import date, datetime

router = APIRouter()


class UsuarioAutenticado(BaseModel):
    id: int


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


# Dependências esperadas na aplicação:
# - get_db(): retorna sessão/conexão com o banco
# - get_current_user(): retorna o usuário autenticado via token
#
# Ajuste os imports/implementações dessas dependências conforme sua aplicação.
def get_db():
    raise NotImplementedError


def get_current_user() -> UsuarioAutenticado:
    raise NotImplementedError


@router.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(
    id: int,
    db=Depends(get_db),
    usuario_autenticado: UsuarioAutenticado = Depends(get_current_user),
):
    pedido = db.execute(
        """
        SELECT id, usuario_id, numero, data, valor_total, status
        FROM pedidos
        WHERE id = :id
        """,
        {"id": id},
    ).fetchone()

    if not pedido or pedido["usuario_id"] != usuario_autenticado.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado",
        )

    itens = db.execute(
        """
        SELECT produto_nome, quantidade, preco_unitario
        FROM itens_pedido
        WHERE pedido_id = :pedido_id
        ORDER BY produto_nome
        """,
        {"pedido_id": pedido["id"]},
    ).fetchall()

    return PedidoOut(
        numero=pedido["numero"],
        data=pedido["data"],
        status=pedido["status"],
        valor_total=pedido["valor_total"],
        itens=[
            ItemPedidoOut(
                produto_nome=item["produto_nome"],
                quantidade=item["quantidade"],
                preco_unitario=item["preco_unitario"],
            )
            for item in itens
        ],
    )