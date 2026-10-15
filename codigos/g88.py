from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()


class Product(BaseModel):
    id: int
    name: str
    category: str
    price: float
    in_stock: bool


MOCK_PRODUCTS = [
    Product(id=1, name="Notebook", category="eletronicos", price=4500.0, in_stock=True),
    Product(id=2, name="Mouse", category="eletronicos", price=120.0, in_stock=True),
    Product(id=3, name="Teclado", category="eletronicos", price=250.0, in_stock=False),
    Product(id=4, name="Cadeira", category="moveis", price=899.9, in_stock=True),
    Product(id=5, name="Mesa", category="moveis", price=1299.0, in_stock=False),
]


@app.get("/products", response_model=List[Product])
def list_products(
    name: Optional[str] = Query(None, description="Filtra por nome"),
    category: Optional[str] = Query(None, description="Filtra por categoria"),
    min_price: Optional[float] = Query(None, ge=0, description="Preço mínimo"),
    max_price: Optional[float] = Query(None, ge=0, description="Preço máximo"),
    in_stock: Optional[bool] = Query(None, description="Filtra por disponibilidade"),
):
    results = MOCK_PRODUCTS

    if name:
        results = [p for p in results if name.lower() in p.name.lower()]
    if category:
        results = [p for p in results if p.category.lower() == category.lower()]
    if min_price is not None:
        results = [p for p in results if p.price >= min_price]
    if max_price is not None:
        results = [p for p in results if p.price <= max_price]
    if in_stock is not None:
        results = [p for p in results if p.in_stock == in_stock]

    return results