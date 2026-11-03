import os
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine, select, Table, MetaData, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import Session
from tcc_t06_infra import usuario_atual

db_path = os.getenv("TCC_DB_PATH")
engine = create_engine(f"sqlite:///{db_path}", future=True)
metadata = MetaData()

pedidos = Table(
    "pedidos", metadata,
    Column("id", Integer, primary_key=True),
    Column("usuario_id", Integer),
    Column("numero", String),
    Column("data", String),
    Column("valor_total", Float),
    Column("status", String),
)

itens_pedido = Table(
    "itens_pedido", metadata,
    Column("id", Integer, primary_key=True),
    Column("pedido_id", Integer, ForeignKey("pedidos.id")),
    Column("produto_nome", String),
    Column("quantidade", Integer),
    Column("preco_unitario", Float),
)

app = FastAPI()


@app.get("/pedidos/{id}")
def get_pedido(id: int, usuario: dict = Depends(usuario_atual)):
    with Session(engine) as session:
        stmt_pedido = select(
            pedidos.c.numero,
            pedidos.c.data,
            pedidos.c.status,
            pedidos.c.valor_total,
            pedidos.c.usuario_id,
            pedidos.c.id,
        ).where(pedidos.c.id == id)
        pedido = session.execute(stmt_pedido).first()
        if not pedido or pedido.usuario_id != usuario["id"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        stmt_itens = select(
            itens_pedido.c.produto_nome,
            itens_pedido.c.quantidade,
            itens_pedido.c.preco_unitario,
        ).where(itens_pedido.c.pedido_id == id)
        itens = session.execute(stmt_itens).all()
        return {
            "numero": pedido.numero,
            "data": pedido.data,
            "status": pedido.status,
            "valor_total": pedido.valor_total,
            "itens": [
                {
                    "produto_nome": i.produto_nome,
                    "quantidade": i.quantidade,
                    "preco_unitario": i.preco_unitario,
                }
                for i in itens
            ],
        }