from fastapi import FastAPI, HTTPException

app = FastAPI()

orders = {
    1: {"id": 1, "customer": "João", "total": 150.0, "status": "paid"},
    2: {"id": 2, "customer": "Maria", "total": 89.9, "status": "pending"},
}

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return order