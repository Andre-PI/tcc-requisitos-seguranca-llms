import os
import sqlite3
from typing import Any, Dict, List

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

from tcc_t06_infra import usuario_atual

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
    itens: List[ItemPedidoOut]


def _get_db_path() -> str:
    db_path = os.environ.get("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH nao definido")
    return db_path


def _fetch_pedido(pedido_id: int, usuario_id: int) -> Dict[str, Any] | None:
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        pedido = conn.execute(
            """
            SELECT id, numero, data, valor_total, status
            FROM pedidos
            WHERE id = ? AND usuario_id = ?
            """,
            (pedido_id, usuario_id),
        ).fetchone()

        if pedido is None:
            return None

        itens_rows = conn.execute(
            """
            SELECT produto_nome, quantidade, preco_unitario
            FROM itens_pedido
            WHERE pedido_id = ?
            ORDER BY id
            """,
            (pedido_id,),
        ).fetchall()

        itens = [
            {
                "produto_nome": row["produto_nome"],
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            }
            for row in itens_rows
        ]

        return {
            "numero": pedido["numero"],
            "data": pedido["data"],
            "status": pedido["status"],
            "valor_total": pedido["valor_total"],
            "itens": itens,
        }
    finally:
        conn.close()


@app.get("/pedidos/{id}", response_model=PedidoOut)
def get_pedido(id: int, usuario: dict = Depends(usuario_atual)):
    pedido = _fetch_pedido(id, usuario["id"])
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    return pedido