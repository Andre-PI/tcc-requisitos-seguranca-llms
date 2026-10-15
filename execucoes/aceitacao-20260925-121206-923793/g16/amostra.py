from fastapi import FastAPI, Query
from typing import Optional, List
from pydantic import BaseModel
import sqlite3

app = FastAPI()

class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

def get_db_connection():
    conn = sqlite3.connect('produtos.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/produtos", response_model=List[Produto])
def buscar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None),
    preco_max: Optional[float] = Query(None),
    ordenar_por: Optional[str] = Query(None, regex="^(preco|nome)$")
):
    query = "SELECT id, nome, categoria, preco, estoque FROM produtos WHERE 1=1"
    params = []

    if nome:
        query += " AND nome LIKE ?"
        params.append(f"%{nome}%")
    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)
    if preco_min is not None:
        query += " AND preco >= ?"
        params.append(preco_min)
    if preco_max is not None:
        query += " AND preco <= ?"
        params.append(preco_max)
    if ordenar_por:
        query += f" ORDER BY {ordenar_por} COLLATE NOCASE"

    conn = get_db_connection()
    cursor = conn.execute(query, params)
    produtos = cursor.fetchall()
    conn.close()

    return [Produto(**dict(produto)) for produto in produtos]