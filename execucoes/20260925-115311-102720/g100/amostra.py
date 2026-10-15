from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Pedido(BaseModel):
    id: int
    cliente: str
    total: float
    status: str

# Exemplo de "banco" em memória
pedidos_db = {
    1: {"id": 1, "cliente": "João", "total": 150.0, "status": "pago"},
    2: {"id": 2, "cliente": "Maria", "total": 89.9, "status": "pendente"},
}

@app.get("/pedidos/{pedido_id}", response_model=Pedido)
def obter_pedido(pedido_id: int):
    pedido = pedidos_db.get(pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido