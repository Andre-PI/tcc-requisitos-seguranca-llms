from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class Pedido(BaseModel):
    id: int
    cliente: str
    total: float
    status: str
    observacao: Optional[str] = None

PEDIDOS_DB = {
    1: {"id": 1, "cliente": "João Silva", "total": 150.75, "status": "processando"},
    2: {"id": 2, "cliente": "Maria Souza", "total": 89.90, "status": "enviado"},
    3: {"id": 3, "cliente": "Carlos Lima", "total": 245.00, "status": "entregue"},
}

@app.get("/pedidos/{pedido_id}", response_model=Pedido)
def obter_pedido(pedido_id: int):
    pedido = PEDIDOS_DB.get(pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido