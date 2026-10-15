from fastapi import FastAPI, HTTPException

app = FastAPI()

# Exemplo de dados de pedidos
pedidos = {
    1: {"id": 1, "produto": "Livro", "quantidade": 2, "preco": 50.0},
    2: {"id": 2, "produto": "Caneta", "quantidade": 10, "preco": 2.5},
    3: {"id": 3, "produto": "Caderno", "quantidade": 5, "preco": 15.0},
}

@app.get("/pedido/{pedido_id}")
def obter_pedido(pedido_id: int):
    pedido = pedidos.get(pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido