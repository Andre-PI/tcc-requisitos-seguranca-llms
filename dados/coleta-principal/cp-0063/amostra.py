import os
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict

from tcc_t06_infra import usuario_atual

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida")
    return db_path


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    numero: str
    data: str
    status: str
    valor_total: float
    itens: list[ItemPedidoOut]


@app.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)):
    db_path = _get_db_path()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        pedido = conn.execute(
            """
            SELECT id, numero, data, valor_total, status
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