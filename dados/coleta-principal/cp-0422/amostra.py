import os
import sqlite3
from typing import Any

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from tcc_t06_infra import usuario_atual

DB_PATH = os.getenv("TCC_DB_PATH")

app = FastAPI()


class ItemPedidoOut(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float

    model_config = ConfigDict(from_attributes=True)


class PedidoOut(BaseModel):
    numero: str
    data: str
    status: str
    valor_total: float
    itens: list[ItemPedidoOut]

    model_config = ConfigDict(from_attributes=True)


def get_conn() -> sqlite3.Connection:
    if not DB_PATH:
        raise RuntimeError("TCC_DB_PATH nao definido")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)):
    conn = get_conn()
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
            raise HTTPException(status_code=404, detail="Pedido nao encontrado")

        if int(pedido["usuario_id"]) != int(usuario["id"]):
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