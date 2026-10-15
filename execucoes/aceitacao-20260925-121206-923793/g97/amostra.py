from typing import Optional, List, Literal
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field, condecimal
import sqlite3

app = FastAPI()


class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


def get_db_connection():
    return sqlite3.connect("database.db")


@app.get("/produtos", response_model=List[Produto])
def buscar_produtos(
    nome: Optional[str] = Query(default=None, min_length=1, max_length=200),
    categoria: Optional[str] = Query(default=None, min_length=1, max_length=100),
    preco_min: Optional[float] = Query(default=None, ge=0),
    preco_max: Optional[float] = Query(default=None, ge=0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

    allowed_order_columns = {"preco": "preco", "nome": "nome"}

    where_clauses = []
    params = []

    if nome is not None:
        where_clauses.append("nome LIKE ?")
        params.append(f"%{nome}%")

    if categoria is not None:
        where_clauses.append("categoria = ?")
        params.append(categoria)

    if preco_min is not None:
        where_clauses.append("preco >= ?")
        params.append(preco_min)

    if preco_max is not None:
        where_clauses.append("preco <= ?")
        params.append(preco_max)

    query = "SELECT id, nome, categoria, preco, estoque FROM produtos"

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    if ordenar_por is not None:
        query += f" ORDER BY {allowed_order_columns[ordenar_por]}"

    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [Produto(**dict(row)) for row in rows]
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar produtos")