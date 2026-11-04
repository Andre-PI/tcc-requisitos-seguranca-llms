import os
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException, Depends

try:
    from tcc_t06_infra import usuario_atual
except Exception:  # pragma: no cover
    def usuario_atual() -> dict[str, int]:
        raise HTTPException(status_code=401, detail="Unauthorized")


DB_PATH = os.environ.get("TCC_DB_PATH")

app = FastAPI()


def get_connection() -> sqlite3.Connection:
    if not DB_PATH:
        raise HTTPException(status_code=500, detail="TCC_DB_PATH not set")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/pedidos/{id}")
def obter_pedido(id: int, usuario: dict[str, int] = Depends(usuario_atual)) -> dict[str, Any]:
    conn = get_connection()
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
            raise HTTPException(status_code=404, detail="Pedido não encontrado")

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