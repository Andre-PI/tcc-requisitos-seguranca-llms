from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field

from tcc_t06_infra import usuario_atual

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH nao definido")


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero: str
    data: str
    status: str
    valor_total: float
    itens: list[ItemPedidoOut]


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(
    id: int = Path(..., ge=1),
    usuario: dict[str, Any] = Depends(usuario_atual),
):
    usuario_id = usuario["id"]

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

        if pedido is None or pedido["usuario_id"] != usuario_id:
            raise HTTPException(status_code=404, detail="Pedido nao encontrado")

        itens = conn.execute(
            """
            SELECT produto_nome, quantidade, preco_unitario
            FROM itens_pedido
            WHERE pedido_id = ?
            ORDER BY id
            """,
            (id,),
        ).fetchall()

        return {
            "numero": pedido["numero"],
            "data": pedido["data"],
            "status": pedido["status"],
            "valor_total": float(pedido["valor_total"]),
            "itens": [
                {
                    "produto_nome": item["produto_nome"],
                    "quantidade": item["quantidade"],
                    "preco_unitario": float(item["preco_unitario"]),
                }
                for item in itens
            ],
        }
    finally:
        conn.close()