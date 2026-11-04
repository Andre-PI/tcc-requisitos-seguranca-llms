import os
import sqlite3
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from tcc_t06_infra import usuario_atual

app = FastAPI()


DB_PATH = os.environ.get("TCC_DB_PATH")


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


def _get_connection() -> sqlite3.Connection:
    if not DB_PATH:
        raise RuntimeError("TCC_DB_PATH nao definido")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/pedidos/{id}", response_model=PedidoOut)
def get_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)):
    usuario_id = usuario.get("id")
    if usuario_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nao autenticado")

    with _get_connection() as conn:
        pedido = conn.execute(
            """
            SELECT id, numero, data, status, valor_total
            FROM pedidos
            WHERE id = ? AND usuario_id = ?
            """,
            (id, usuario_id),
        ).fetchone()

        if pedido is None:
            existente = conn.execute(
                "SELECT 1 FROM pedidos WHERE id = ?",
                (id,),
            ).fetchone()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido nao encontrado")

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