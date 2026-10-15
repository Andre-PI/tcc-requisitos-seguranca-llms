from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional, List, Literal

app = FastAPI()


class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


# Exemplo de fonte de dados em memória.
# Substitua por acesso ao banco de dados conforme necessário.
PRODUTOS_DB = [
    {"id": 1, "nome": "Notebook Gamer", "categoria": "Eletrônicos", "preco": 4500.0, "estoque": 10},
    {"id": 2, "nome": "Mouse Sem Fio", "categoria": "Periféricos", "preco": 120.0, "estoque": 50},
    {"id": 3, "nome": "Teclado Mecânico", "categoria": "Periféricos", "preco": 350.0, "estoque": 25},
    {"id": 4, "nome": "Cadeira Gamer", "categoria": "Móveis", "preco": 900.0, "estoque": 8},
]


@app.get("/produtos", response_model=List[Produto])
def buscar_produtos(
    nome: Optional[str] = Query(None, description="Busca parcial pelo nome"),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None, ge=0),
    preco_max: Optional[float] = Query(None, ge=0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(None),
):
    produtos = PRODUTOS_DB

    if nome is not None:
        nome_lower = nome.lower()
        produtos = [p for p in produtos if nome_lower in p["nome"].lower()]

    if categoria is not None:
        categoria_lower = categoria.lower()
        produtos = [p for p in produtos if p["categoria"].lower() == categoria_lower]

    if preco_min is not None:
        produtos = [p for p in produtos if p["preco"] >= preco_min]

    if preco_max is not None:
        produtos = [p for p in produtos if p["preco"] <= preco_max]

    if ordenar_por == "preco":
        produtos = sorted(produtos, key=lambda p: p["preco"])
    elif ordenar_por == "nome":
        produtos = sorted(produtos, key=lambda p: p["nome"].lower())

    return produtos