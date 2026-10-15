from fastapi import FastAPI, Query
from typing import Optional, List
from pydantic import BaseModel

app = FastAPI()

class Product(BaseModel):
    id: int
    name: str
    category: str
    price: float
    in_stock: bool

# Simulação de banco de dados
products_db = [
    Product(id=1, name="Notebook", category="Eletrônicos", price=2500.0, in_stock=True),
    Product(id=2, name="Mouse", category="Eletrônicos", price=50.0, in_stock=True),
    Product(id=3, name="Cadeira", category="Móveis", price=350.0, in_stock=False),
    Product(id=4, name="Mesa", category="Móveis", price=1200.0, in_stock=True),
    Product(id=5, name="Livro Python", category="Livros", price=120.0, in_stock=True),
]

@app.get("/products", response_model=List[Product])
def get_products(
    name: Optional[str] = Query(None, description="Nome do produto"),
    category: Optional[str] = Query(None, description="Categoria do produto"),
    price_min: Optional[float] = Query(None, ge=0, description="Preço mínimo"),
    price_max: Optional[float] = Query(None, ge=0, description="Preço máximo"),
    in_stock: Optional[bool] = Query(None, description="Produto em estoque"),
):
    results = products_db
    if name:
        results = [p for p in results if name.lower() in p.name.lower()]
    if category:
        results = [p for p in results if p.category.lower() == category.lower()]
    if price_min is not None:
        results = [p for p in results if p.price >= price_min]
    if price_max is not None:
        results = [p for p in results if p.price <= price_max]
    if in_stock is not None:
        results = [p for p in results if p.in_stock == in_stock]
    return results