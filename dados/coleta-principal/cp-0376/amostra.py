import os
import sqlite3
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from tcc_t06_infra import usuario_atual

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

app = FastAPI()


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    produto_nome: str
    quantidade: int = Field(ge=1)
    preco_unitario: float = Field(ge=0)


class PedidoOut(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    numero: str
    data: str
    status: str
    valor_total: float = Field(ge=0)
    itens: list[ItemPedidoOut]


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@app.get("/pedidos/{id}", response_model=PedidoOut, response_model_exclude_none=True)
def obter_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)):
    usuario_id = usuario.get("id")
    if not isinstance(usuario_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    with get_connection() as conn:
        pedido = conn.execute(
            """
            SELECT id, numero, data, valor_total, status
            FROM pedidos
            WHERE id = ? AND usuario_id = ?
            """,
            (id, usuario_id),
        ).fetchone()

        if pedido is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

        itens = conn.execute(
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
        valor_total=float(pedido["valor_total"]),
        itens=[
            ItemPedidoOut(
                produto_nome=item["produto_nome"],
                quantidade=int(item["quantidade"]),
                preco_unitario=float(item["preco_unitario"]),
            )
            for item in itens
        ],
    )