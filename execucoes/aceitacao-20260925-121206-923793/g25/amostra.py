from fastapi import FastAPI, HTTPException

app = FastAPI()

# Dados de exemplo
pedidos = {
    1: {"id": 1, "produto": "Camisa", "quantidade": 3, "preco": 59.90},
    2: {"id": 2, "produto": "Calça", "quantidade": 1, "preco": 120.00},
    3: {"id": 3, "produto": "Tênis", "quantidade": 2, "preco": 250.50},
}

@app.get("/pedido/{pedido_id}")
def obter_pedido(pedido_id: int):
    pedido = pedidos.get(pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido