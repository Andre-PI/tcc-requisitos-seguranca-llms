from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()


class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    em_estoque: bool


PRODUTOS = [
    Produto(id=1, nome="Notebook Gamer", categoria="eletronicos", preco=5500.0, em_estoque=True),
    Produto(id=2, nome="Mouse", categoria="eletronicos", preco=120.0, em_estoque=True),
    Produto(id=3, nome="Cadeira", categoria="moveis", preco=899.9, em_estoque=False),
    Produto(id=4, nome="Mesa", categoria="moveis", preco=1200.0, em_estoque=True),
]


@app.get("/produtos", response_model=List[Produto])
def listar_produtos(
    nome: Optional[str] = Query(None, description="Filtra por nome"),
    categoria: Optional[str] = Query(None, description="Filtra por categoria"),
    preco_min: Optional[float] = Query(None, ge=0, description="Preço mínimo"),
    preco_max: Optional[float] = Query(None, ge=0, description="Preço máximo"),
    em_estoque: Optional[bool] = Query(None, description="Filtra por disponibilidade"),
):
    resultados = PRODUTOS

    if nome is not None:
        resultados = [p for p in resultados if nome.lower() in p.nome.lower()]

    if categoria is not None:
        resultados = [p for p in resultados if p.categoria.lower() == categoria.lower()]

    if preco_min is not None:
        resultados = [p for p in resultados if p.preco >= preco_min]

    if preco_max is not None:
        resultados = [p for p in resultados if p.preco <= preco_max]

    if em_estoque is not None:
        resultados = [p for p in resultados if p.em_estoque == em_estoque]

    return resultados