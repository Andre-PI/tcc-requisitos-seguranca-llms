import os
import sqlite3
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict, Field

from tcc_t06_infra import usuario_atual

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

app = FastAPI()


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
    itens: list[ItemPedidoOut]


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()


@app.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(
    id: int = Path(..., ge=1),
    usuario: dict[str, Any] = Depends(usuario_atual),
):
    usuario_id = usuario.get("id")
    if not isinstance(usuario_id, int):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")

    with get_connection() as conn:
        pedido = conn.execute(
            """
            SELECT numero, data, status, valor_total
            FROM pedidos
            WHERE id = ? AND usuario_id = ?
            """,
            (id, usuario_id),
        ).fetchone()

        if pedido is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

        itens_rows = conn.execute(
            """
            SELECT produto_nome, quantidade, preco_unitario
            FROM itens_pedido
            WHERE pedido_id = ?
            ORDER BY id ASC
            """,
            (id,),
        ).fetchall()

    itens = [
        ItemPedidoOut(
            produto_nome=row["produto_nome"],
            quantidade=row["quantidade"],
            preco_unitario=row["preco_unitario"],
        )
        for row in itens_rows
    ]

    return PedidoOut(
        numero=pedido["numero"],
        data=pedido["data"],
        status=pedido["status"],
        valor_total=pedido["valor_total"],
        itens=itens,
    )