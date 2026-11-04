import os
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict

from tcc_t06_infra import usuario_atual

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

app = FastAPI()


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    numero: str
    data: str
    status: str
    valor_total: float
    itens: list[ItemPedidoOut]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)):
    conn = _get_conn()
    try:
        pedido = conn.execute(
            """
            SELECT numero, data, status, valor_total
            FROM pedidos
            WHERE id = ? AND usuario_id = ?
            """,
            (id, usuario["id"]),
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