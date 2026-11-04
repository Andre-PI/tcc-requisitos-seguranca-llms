import os
import sqlite3
from typing import Any

from fastapi import FastAPI, Depends, HTTPException

from tcc_t06_infra import usuario_atual

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definido")
    return db_path


def _fetch_pedido(pedido_id: int, usuario_id: int) -> dict[str, Any] | None:
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        pedido = conn.execute(
            """
            SELECT id, usuario_id, numero, data, valor_total, status
            FROM pedidos
            WHERE id = ? AND usuario_id = ?
            """,
            (pedido_id, usuario_id),
        ).fetchone()

        if pedido is None:
            return None

        itens = conn.execute(
            """
            SELECT produto_nome, quantidade, preco_unitario
            FROM itens_pedido
            WHERE pedido_id = ?
            ORDER BY id
            """,
            (pedido_id,),
        ).fetchall()

        return {
            "numero": pedido["numero"],
            "data": pedido["data"],
            "status": pedido["status"],
            "valor_total": pedido["valor_total"],
            "itens": [
                {
                    "produto_nome": item["produto_nome"],
                    "quantidade": item["quantidade"],
                    "preco_unitario": item["preco_unitario"],
                }
                for item in itens
            ],
        }
    finally:
        conn.close()


@app.get("/pedidos/{id}")
def get_pedido(id: int, usuario: dict = Depends(usuario_atual)):
    pedido = _fetch_pedido(id, int(usuario["id"]))
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido