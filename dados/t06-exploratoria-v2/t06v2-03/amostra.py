import os
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine, select, Table, Column, Integer, String, Float, MetaData, ForeignKey
from sqlalchemy.orm import Session, sessionmaker
from tcc_t06_infra import usuario_atual

db_path = os.getenv("TCC_DB_PATH")
engine = create_engine(f"sqlite:///{db_path}", future=True)
SessionLocal = sessionmaker(bind=engine, future=True)

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
def get_pedido(id: int, user=Depends(usuario_atual)):
    with SessionLocal() as session:
        stmt_pedido = select(pedidos).where(pedidos.c.id == id)
        pedido = session.execute(stmt_pedido).first()
        if not pedido:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        pedido = pedido._mapping
        stmt_itens = select(itens_pedido).where(itens_pedido.c.pedido_id == id)
        itens = session.execute(stmt_itens).all()
        itens_list = [
            {
                "produto_nome": i._mapping["produto_nome"],
                "quantidade": i._mapping["quantidade"],
                "preco_unitario": i._mapping["preco_unitario"],
            }
            for i in itens
        ]
        return {
            "numero": pedido["numero"],
            "data": pedido["data"],
            "status": pedido["status"],
            "valor_total": pedido["valor_total"],
            "itens": itens_list,
        }