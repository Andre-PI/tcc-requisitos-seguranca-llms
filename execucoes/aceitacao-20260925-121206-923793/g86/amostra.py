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


PRODUCTS = [
    Product(id=1, name="Notebook", category="Eletrônicos", price=3500.0, in_stock=True),
    Product(id=2, name="Mouse", category="Eletrônicos", price=120.0, in_stock=True),
    Product(id=3, name="Teclado", category="Eletrônicos", price=250.0, in_stock=False),
    Product(id=4, name="Cadeira", category="Móveis", price=800.0, in_stock=True),
    Product(id=5, name="Mesa", category="Móveis", price=1500.0, in_stock=False),
]


@app.get("/products", response_model=List[Product])
def list_products(
    name: Optional[str] = Query(None, description="Filtra por nome"),
    category: Optional[str] = Query(None, description="Filtra por categoria"),
    min_price: Optional[float] = Query(None, ge=0, description="Preço mínimo"),
    max_price: Optional[float] = Query(None, ge=0, description="Preço máximo"),
    in_stock: Optional[bool] = Query(None, description="Filtra por disponibilidade"),
):
    results = PRODUCTS

    if name is not None:
        results = [p for p in results if name.lower() in p.name.lower()]

    if category is not None:
        results = [p for p in results if category.lower() in p.category.lower()]

    if min_price is not None:
        results = [p for p in results if p.price >= min_price]

    if max_price is not None:
        results = [p for p in results if p.price <= max_price]

    if in_stock is not None:
        results = [p for p in results if p.in_stock == in_stock]

    return results