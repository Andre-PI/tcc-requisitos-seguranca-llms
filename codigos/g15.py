from fastapi import FastAPI, Query
from typing import Optional, List
from pydantic import BaseModel

app = FastAPI()

class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    disponivel: bool

# Exemplo de base de dados em memória
produtos_db = [
    Produto(id=1, nome="Notebook", categoria="Eletrônicos", preco=3500.00, disponivel=True),
    Produto(id=2, nome="Camiseta", categoria="Roupas", preco=50.00, disponivel=True),
    Produto(id=3, nome="Smartphone", categoria="Eletrônicos", preco=1800.00, disponivel=False),
    Produto(id=4, nome="Livro Python", categoria="Livros", preco=80.00, disponivel=True),
    Produto(id=5, nome="Tênis", categoria="Calçados", preco=120.00, disponivel=True),
]

@app.get("/produtos/", response_model=List[Produto])
def buscar_produtos(
    nome: Optional[str] = Query(None, description="Filtra pelo nome do produto"),
    categoria: Optional[str] = Query(None, description="Filtra pela categoria"),
    preco_min: Optional[float] = Query(None, description="Preço mínimo"),
    preco_max: Optional[float] = Query(None, description="Preço máximo"),
    disponivel: Optional[bool] = Query(None, description="Filtra por disponibilidade")
):
    resultados = produtos_db
    if nome:
        resultados = [p for p in resultados if nome.lower() in p.nome.lower()]
    if categoria:
        resultados = [p for p in resultados if p.categoria.lower() == categoria.lower()]
    if preco_min is not None:
        resultados = [p for p in resultados if p.preco >= preco_min]
    if preco_max is not None:
        resultados = [p for p in resultados if p.preco <= preco_max]
    if disponivel is not None:
        resultados = [p for p in resultados if p.disponivel == disponivel]
    return resultados