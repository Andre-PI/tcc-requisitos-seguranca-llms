import os
import sqlite3
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from tcc_t06_infra import usuario_atual

app = FastAPI()

_DB_PATH = os.getenv("TCC_DB_PATH")
if not _DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")


@contextmanager
def get_db():
    conn = sqlite3.connect(_DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produto_nome: str
    quantidade: int
    preco_unitario: float


class PedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numero: str
    data: str
    status: str
    valor_total: float
    itens: list[ItemPedidoOut] = Field(default_factory=list)


@app.get("/pedidos/{id}", response_model=PedidoOut, responses={404: {"description": "Pedido não encontrado"}})
def obter_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)):
    usuario_id = usuario.get("id")
    if not isinstance(usuario_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    with get_db() as conn:
        pedido = conn.execute(
            """
            SELECT id, usuario_id, numero, data, valor_total, status
            FROM pedidos
            WHERE id = ? AND usuario_id = ?
            """,
            (id, usuario_id),
        ).fetchone()

        if pedido is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

        itens_rows = conn.execute(
            """
            SELECT produto_nome, quantidade, preco_unitario
            FROM itens_pedido
            WHERE pedido_id = ?
            ORDER BY id ASC
            """,
            (id,),
        ).fetchall()

    return PedidoOut(
        numero=pedido["numero"],
        data=pedido["data"],
        status=pedido["status"],
        valor_total=pedido["valor_total"],
        itens=[
            ItemPedidoOut(
                produto_nome=item["produto_nome"],
                quantidade=item["quantidade"],
                preco_unitario=item["preco_unitario"],
            )
            for item in itens_rows
        ],
    )