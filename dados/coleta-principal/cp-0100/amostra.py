import os
import sqlite3
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

from tcc_t06_infra import usuario_atual

app = FastAPI()


def get_db_path() -> str:
    db_path = os.environ.get("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definido")
    return db_path


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


@app.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(id: int, usuario: dict = Depends(usuario_atual)):
    db_path = get_db_path()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        pedido = conn.execute(
            """
            SELECT id, numero, data, valor_total, status
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