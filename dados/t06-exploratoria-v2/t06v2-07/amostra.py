import os
from typing import Any

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, text

from tcc_t06_infra import usuario_atual

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

app = FastAPI()


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


@app.get("/pedidos/{id}", response_model=PedidoOut)
def obter_pedido(id: int, usuario: dict[str, Any] = Depends(usuario_atual)):
    usuario_id = usuario["id"]

    with engine.connect() as conn:
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
            raise HTTPException(status_code=404, detail="Pedido não encontrado")

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