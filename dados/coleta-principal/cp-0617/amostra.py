import os
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from tcc_t06_infra import usuario_atual

app = FastAPI(title="Pedidos API")

_DB_PATH = os.getenv("TCC_DB_PATH")
if not _DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

if _DB_PATH.startswith("sqlite:///"):
    _DATABASE_URL = _DB_PATH
elif _DB_PATH.startswith("sqlite:"):
    _DATABASE_URL = _DB_PATH
else:
    _DATABASE_URL = f"sqlite:///{_DB_PATH}"

_engine: Engine = create_engine(
    _DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)


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
def obter_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)) -> PedidoOut:
    usuario_id = usuario.get("id")
    if not isinstance(usuario_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    with _engine.connect() as conn:
        pedido = conn.execute(
            text(
                """
                SELECT id, usuario_id, numero, data, valor_total, status
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
        numero=str(pedido["numero"]),
        data=str(pedido["data"]),
        status=str(pedido["status"]),
        valor_total=float(pedido["valor_total"]),
        itens=[
            ItemPedidoOut(
                produto_nome=str(item["produto_nome"]),
                quantidade=int(item["quantidade"]),
                preco_unitario=float(item["preco_unitario"]),
            )
            for item in itens
        ],
    )