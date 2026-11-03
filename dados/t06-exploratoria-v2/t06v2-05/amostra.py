import os
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine, select, Table, Column, Integer, String, Float, MetaData, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from tcc_t06_infra import usuario_atual

app = FastAPI()

db_path = os.environ["TCC_DB_PATH"]
engine = create_engine(f"sqlite:///{db_path}", future=True)
metadata = MetaData()

pedidos = Table(
    "pedidos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("usuario_id", Integer),
    Column("numero", String),
    Column("data", String),
    Column("valor_total", Float),
    Column("status", String),
)

itens_pedido = Table(
    "itens_pedido",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("pedido_id", Integer, ForeignKey("pedidos.id")),
    Column("produto_nome", String),
    Column("quantidade", Integer),
    Column("preco_unitario", Float),
)

@app.get("/pedidos/{id}")
def get_pedido(id: int, user: dict = Depends(usuario_atual)):
    with engine.connect() as conn:
        stmt_pedido = select(
            pedidos.c.id,
            pedidos.c.usuario_id,
            pedidos.c.numero,
            pedidos.c.data,
            pedidos.c.valor_total,
            pedidos.c.status,
        ).where(pedidos.c.id == id)
        pedido = conn.execute(stmt_pedido).first()
        if not pedido or pedido.usuario_id != user["id"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        stmt_itens = select(
            itens_pedido.c.produto_nome,
            itens_pedido.c.quantidade,
            itens_pedido.c.preco_unitario,
        ).where(itens_pedido.c.pedido_id == id)
        itens = [dict(row._mapping) for row in conn.execute(stmt_itens).all()]
    return {
        "numero": pedido.numero,
        "data": pedido.data,
        "status": pedido.status,
        "valor_total": pedido.valor_total,
        "itens": itens,
    }