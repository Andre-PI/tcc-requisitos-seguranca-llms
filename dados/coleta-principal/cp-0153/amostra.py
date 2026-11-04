import os
import sqlite3
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict

from tcc_t06_infra import usuario_atual

app = FastAPI()


class ItemPedido(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoResponse(BaseModel):
    numero: str
    data: str
    status: str
    valor_total: float
    itens: List[ItemPedido]


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definido")
    return db_path


def _fetch_pedido(pedido_id: int):
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        pedido = conn.execute(
            """
            SELECT id, numero, data, status, valor_total
            FROM pedidos
            WHERE id = ?
            """,
            (pedido_id,),
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


@app.get("/pedidos/{id}", response_model=PedidoResponse)
def get_pedido(id: int, usuario=Depends(usuario_atual)):
    pedido = _fetch_pedido(id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido