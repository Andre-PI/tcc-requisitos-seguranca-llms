import os
import sqlite3
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from tcc_t06_infra import usuario_atual

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

app = FastAPI(title="Pedidos API")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numero: str
    data: str
    status: str
    valor_total: float
    itens: list[ItemPedidoOut] = Field(default_factory=list)


@app.get("/pedidos/{id}", response_model=PedidoOut, responses={404: {"description": "Pedido não encontrado"}})
def obter_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)) -> PedidoOut:
    usuario_id = usuario.get("id")
    if not isinstance(usuario_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inválido")

    if id <= 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    conn = _get_connection()
    try:
        pedido = conn.execute(
            """
            SELECT id, usuario_id, numero, data, valor_total, status
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

        def _to_float(value: Any) -> float:
            if value is None:
                return 0.0
            if isinstance(value, Decimal):
                return float(value)
            return float(value)

        return PedidoOut(
            numero=pedido["numero"],
            data=pedido["data"],
            status=pedido["status"],
            valor_total=_to_float(pedido["valor_total"]),
            itens=[
                ItemPedidoOut(
                    produto_nome=item["produto_nome"],
                    quantidade=int(item["quantidade"]),
                    preco_unitario=_to_float(item["preco_unitario"]),
                )
                for item in itens
            ],
        )
    finally:
        conn.close()