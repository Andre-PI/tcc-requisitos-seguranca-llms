from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from tcc_t06_infra import usuario_atual

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definido")
    return db_path


ENGINE: Engine = create_engine(f"sqlite:///{_get_db_path()}", future=True)


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    usuario_id = usuario["id"]

    with ENGINE.connect() as conn:
        pedido = conn.execute(
            text(
                """
                SELECT numero, data, status, valor_total
                FROM pedidos
                WHERE id = :id AND usuario_id = :usuario_id
                """
            ),
            {"id": id, "usuario_id": usuario_id},
        ).mappings().first()

        if pedido is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

        itens = conn.execute(
            text(
                """
                SELECT produto_nome, quantidade, preco_unitario
                FROM itens_pedido
                WHERE pedido_id = :pedido_id
                ORDER BY id
                """
            ),
            {"pedido_id": id},
        ).mappings().all()

    return PedidoOut(
        numero=pedido["numero"],
        data=pedido["data"],
        status=pedido["status"],
        valor_total=pedido["valor_total"],
        itens=[ItemPedidoOut(**item) for item in itens],
    )