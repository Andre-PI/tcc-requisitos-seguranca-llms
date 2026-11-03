import os
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine, select, Table, Column, Integer, String, Float, MetaData, ForeignKey
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from tcc_t06_infra import usuario_atual

db_path = os.environ["TCC_DB_PATH"]
engine: Engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

metadata = MetaData()

pedidos = Table(
    "pedidos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("usuario_id", Integer, nullable=False),
    Column("numero", String, nullable=False),
    Column("data", String, nullable=False),
    Column("valor_total", Float, nullable=False),
    Column("status", String, nullable=False),
)

itens_pedido = Table(
    "itens_pedido",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("pedido_id", Integer, ForeignKey("pedidos.id"), nullable=False),
    Column("produto_nome", String, nullable=False),
    Column("quantidade", Integer, nullable=False),
    Column("preco_unitario", Float, nullable=False),
)

app = FastAPI()

@app.get("/pedidos/{id}")
def get_pedido(id: int, usuario: dict = Depends(usuario_atual)):
    with Session(engine) as session:
        stmt_pedido = select(pedidos).where(pedidos.c.id == id, pedidos.c.usuario_id == usuario["id"])
        pedido = session.execute(stmt_pedido).first()
        if not pedido:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

        pedido_data = pedido._mapping
        stmt_itens = select(itens_pedido).where(itens_pedido.c.pedido_id == id)
        itens = session.execute(stmt_itens).all()

        itens_list = [
            {
                "produto_nome": item._mapping["produto_nome"],
                "quantidade": item._mapping["quantidade"],
                "preco_unitario": item._mapping["preco_unitario"],
            } for item in itens
        ]

        return {
            "numero": pedido_data["numero"],
            "data": pedido_data["data"],
            "status": pedido_data["status"],
            "valor_total": pedido_data["valor_total"],
            "itens": itens_list,
        }