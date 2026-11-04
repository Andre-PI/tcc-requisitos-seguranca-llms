import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from tcc_t06_infra import usuario_atual

db_path = os.environ.get("TCC_DB_PATH", "")
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ItemPedidoResponse(BaseModel):
    produto_nome: str
    quantidade: int
    preco_unitario: float

class PedidoResponse(BaseModel):
    numero: str
    data: str
    status: str
    valor_total: float
    itens: List[ItemPedidoResponse]

@app.get("/pedidos/{id}", response_model=PedidoResponse)
def obter_pedido(
    id: int,
    usuario: dict = Depends(usuario_atual),
    db: Session = Depends(get_db)
):
    query_pedido = text("SELECT numero, data, status, valor_total FROM pedidos WHERE id = :id")
    pedido = db.execute(query_pedido, {"id": id}).mappings().first()

    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    query_itens = text("SELECT produto_nome, quantidade, preco_unitario FROM itens_pedido WHERE pedido_id = :pedido_id")
    itens = db.execute(query_itens, {"pedido_id": id}).mappings().all()

    return {
        "numero": pedido["numero"],
        "data": pedido["data"],
        "status": pedido["status"],
        "valor_total": pedido["valor_total"],
        "itens": [
            {
                "produto_nome": item["produto_nome"],
                "quantidade": item["quantidade"],
                "preco_unitario": item["preco_unitario"]
            }
            for item in itens
        ]
    }