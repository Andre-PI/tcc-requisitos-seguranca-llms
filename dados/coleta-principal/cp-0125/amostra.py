import os
import sqlite3
from typing import Any

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from tcc_t06_infra import usuario_atual

app = FastAPI()


def _db_path() -> str:
    path = os.getenv("TCC_DB_PATH")
    if not path:
        raise RuntimeError("TCC_DB_PATH nao definido")
    return path


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


class ItemPedidoOut(BaseModel):
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


@app.get("/pedidos/{id}", response_model=PedidoOut)
def get_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)):
    with _get_connection() as conn:
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

        if pedido["usuario_id"] != usuario["id"]:
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