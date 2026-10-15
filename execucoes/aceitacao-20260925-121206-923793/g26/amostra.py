from fastapi import FastAPI, HTTPException

app = FastAPI()

pedidos = {
    1: {"id": 1, "produto": "Caneta", "quantidade": 10, "preco": 2.5},
    2: {"id": 2, "produto": "Caderno", "quantidade": 5, "preco": 15.0},
    3: {"id": 3, "produto": "Mochila", "quantidade": 1, "preco": 120.0},
}

@app.get("/pedido/{pedido_id}")
def obter_pedido(pedido_id: int):
    pedido = pedidos.get(pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido