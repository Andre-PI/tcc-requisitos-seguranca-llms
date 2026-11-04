import os
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict

from tcc_t06_infra import usuario_atual

app = FastAPI()


class ItemPedido(BaseModel):
    model_config = ConfigDict(extra="ignore")

    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    numero: str
    data: str
    status: str
    valor_total: float
    itens: list[ItemPedido]


def _get_db_path() -> str:
    db_path = os.environ.get("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida.")
    return db_path


def _fetch_pedido(pedido_id: int, usuario_id: int) -> dict[str, Any] | None:
    db_path = _get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        pedido = conn.execute(
            """
            SELECT id, numero, data, status, valor_total
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


@app.get("/pedidos/{id}", response_model=PedidoResponse)
def get_pedido(id: int, usuario: dict = Depends(usuario_atual)):
    pedido = _fetch_pedido(id, int(usuario["id"]))
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido