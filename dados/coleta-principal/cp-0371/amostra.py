import os
import sqlite3
from decimal import Decimal
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_serializer

from tcc_t06_infra import usuario_atual

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

app = FastAPI(title="Pedidos API")


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produto_nome: str
    quantidade: int
    preco_unitario: Decimal

    @field_serializer("preco_unitario")
    def serialize_preco_unitario(self, value: Decimal) -> float:
        return float(value)


class PedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numero: str
    data: str
    status: str
    valor_total: Decimal
    itens: list[ItemPedidoOut]

    @field_serializer("valor_total")
    def serialize_valor_total(self, value: Decimal) -> float:
        return float(value)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/pedidos/{id}", response_model=PedidoOut, responses={404: {"description": "Pedido não encontrado"}})
def obter_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)) -> PedidoOut:
    if id <= 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    usuario_id = usuario.get("id")
    if not isinstance(usuario_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    with _get_connection() as conn:
        pedido = conn.execute(
            """
            SELECT id, numero, data, valor_total, status
            FROM pedidos
            WHERE id = ? AND usuario_id = ?
            """,
            (id, usuario_id),
        ).fetchone()

        if pedido is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

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
        valor_total=Decimal(str(pedido["valor_total"])),
        itens=[
            ItemPedidoOut(
                produto_nome=item["produto_nome"],
                quantidade=int(item["quantidade"]),
                preco_unitario=Decimal(str(item["preco_unitario"])),
            )
            for item in itens
        ],
    )