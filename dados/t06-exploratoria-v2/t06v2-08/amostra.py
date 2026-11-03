from __future__ import annotations

import os
from contextlib import contextmanager
from decimal import Decimal
from typing import Any, Iterator

from fastapi import Depends, FastAPI, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection

from tcc_t06_infra import usuario_atual

DB_PATH = os.getenv("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

ENGINE: Engine = create_engine(
    f"sqlite:///{DB_PATH}",
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},
)

app = FastAPI()


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


@contextmanager
def get_connection() -> Iterator[Connection]:
    conn = ENGINE.connect()
    try:
        yield conn
    finally:
        conn.close()


@app.get("/pedidos/{id}", response_model=PedidoOut, responses={404: {"description": "Pedido não encontrado"}})
def obter_pedido(
    id: int = Path(..., ge=1),
    usuario: dict[str, Any] = Depends(usuario_atual),
) -> PedidoOut:
    usuario_id = usuario.get("id")
    if not isinstance(usuario_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inválido")

    with get_connection() as conn:
        pedido = conn.execute(
            text(
                """
                SELECT numero, data, valor_total, status
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
                ORDER BY id ASC
                """
            ),
            {"pedido_id": id},
        ).mappings().all()

    def as_float(value: Any) -> float:
        if isinstance(value, Decimal):
            return float(value)
        return float(value) if value is not None else 0.0

    return PedidoOut(
        numero=str(pedido["numero"]),
        data=str(pedido["data"]),
        status=str(pedido["status"]),
        valor_total=as_float(pedido["valor_total"]),
        itens=[
            ItemPedidoOut(
                produto_nome=str(item["produto_nome"]),
                quantidade=int(item["quantidade"]),
                preco_unitario=as_float(item["preco_unitario"]),
            )
            for item in itens
        ],
    )