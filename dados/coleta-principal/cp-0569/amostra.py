import os
import sqlite3
from contextlib import contextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, condecimal

try:
    from tcc_t06_infra import usuario_atual
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Dependência tcc_t06_infra indisponível") from exc

app = FastAPI()

_DB_PATH = os.getenv("TCC_DB_PATH")
if not _DB_PATH:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida")


@contextmanager
def get_db():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produto_nome: str
    quantidade: int = Field(ge=1)
    preco_unitario: condecimal(max_digits=12, decimal_places=2)


class PedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numero: str
    data: str
    status: str
    valor_total: condecimal(max_digits=12, decimal_places=2)
    itens: list[ItemPedidoOut]


@app.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(
    id: PositiveInt = Path(..., description="ID do pedido"),
    usuario: dict[str, Any] = Depends(usuario_atual),
):
    usuario_id = usuario.get("id")
    if not isinstance(usuario_id, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não autenticado",
        )

    with get_db() as conn:
        pedido = conn.execute(
            """
            SELECT id, usuario_id, numero, data, valor_total, status
            FROM pedidos
            WHERE id = ? AND usuario_id = ?
            """,
            (id, usuario_id),
        ).fetchone()

        if pedido is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido não encontrado",
            )

        itens = conn.execute(
            """
            SELECT produto_nome, quantidade, preco_unitario
            FROM itens_pedido
            WHERE pedido_id = ?
            ORDER BY id ASC
            """,
            (id,),
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