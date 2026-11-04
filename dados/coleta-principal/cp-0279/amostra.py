import os
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field, ConfigDict

from tcc_t06_infra import usuario_atual

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definido")
    return db_path


@contextmanager
def _get_connection():
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produto_nome: str = Field(..., min_length=1, max_length=255)
    quantidade: int = Field(..., ge=1)
    preco_unitario: Decimal


class PedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numero: str = Field(..., min_length=1, max_length=255)
    data: str
    status: str = Field(..., min_length=1, max_length=100)
    valor_total: Decimal
    itens: list[ItemPedidoOut]


@app.get("/pedidos/{id}", response_model=PedidoOut, responses={404: {"description": "Pedido não encontrado"}})
def obter_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)) -> PedidoOut:
    usuario_id = usuario["id"]

    with _get_connection() as conn:
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
            ORDER BY id
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
                quantidade=item["quantidade"],
                preco_unitario=Decimal(str(item["preco_unitario"])),
            )
            for item in itens
        ],
    )