from __future__ import annotations

import os
import sqlite3
from decimal import Decimal
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict, Field

from tcc_t06_infra import usuario_atual

app = FastAPI(title="Pedidos API")


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definido")
    return db_path


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produto_nome: str = Field(..., min_length=1, max_length=255)
    quantidade: int = Field(..., ge=1)
    preco_unitario: Decimal


class PedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numero: str = Field(..., min_length=1, max_length=100)
    data: str = Field(..., min_length=1, max_length=50)
    status: str = Field(..., min_length=1, max_length=50)
    valor_total: Decimal
    itens: list[ItemPedidoOut]


@app.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(
    id: int = Path(..., ge=1),
    usuario: dict[str, Any] = Depends(usuario_atual),
) -> PedidoOut:
    conn = _get_connection()
    try:
        pedido = conn.execute(
            """
            SELECT id, usuario_id, numero, data, valor_total, status
            FROM pedidos
            WHERE id = ?
            """,
            (id,),
        ).fetchone()

        if pedido is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

        if int(pedido["usuario_id"]) != int(usuario["id"]):
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
            valor_total=_to_decimal(pedido["valor_total"]),
            itens=[
                ItemPedidoOut(
                    produto_nome=item["produto_nome"],
                    quantidade=int(item["quantidade"]),
                    preco_unitario=_to_decimal(item["preco_unitario"]),
                )
                for item in itens
            ],
        )
    finally:
        conn.close()