import os
import sqlite3
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from tcc_t06_infra import usuario_atual

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

app = FastAPI()


class ItemPedidoOut(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoOut(BaseModel):
    numero: str
    data: str
    status: str
    valor_total: float
    itens: list[ItemPedidoOut]


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
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
        raise HTTPException(status_code=401, detail="Não autenticado")

    with get_connection() as conn:
        pedido = conn.execute(
            """
            SELECT id, numero, data, valor_total, status
            FROM pedidos
            WHERE id = ? AND usuario_id = ?
            """,
            (id, usuario_id),
        ).fetchone()

        if pedido is None:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")

        itens = conn.execute(
            """
            SELECT produto_nome, quantidade, preco_unitario
            FROM itens_pedido
            WHERE pedido_id = ?
            ORDER BY id ASC
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
                "quantidade": int(item["quantidade"]),
                "preco_unitario": float(item["preco_unitario"]),
            }
            for item in itens
        ],
    }