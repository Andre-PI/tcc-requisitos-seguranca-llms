import os
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from tcc_t06_infra import usuario_atual

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app = FastAPI()


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
def get_pedido(id: int, usuario=Depends(usuario_atual)):
    usuario_id = usuario["id"]

    with SessionLocal() as session:
        pedido = session.execute(
            text(
                """
                SELECT id, numero, data, valor_total, status
                FROM pedidos
                WHERE id = :id AND usuario_id = :usuario_id
                """
            ),
            {"id": id, "usuario_id": usuario_id},
        ).mappings().first()

        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")

        itens = session.execute(
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