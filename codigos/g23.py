from fastapi import FastAPI, Query, HTTPException
from typing import Optional, List
from pydantic import condecimal, constr, ValidationError
import sqlite3
from sqlite3 import Error
from decimal import Decimal

app = FastAPI()

ALLOWED_ORDER_BY = {"preco", "nome"}

def get_db_connection():
    conn = sqlite3.connect("produtos.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/produtos")
def busca_produtos(
    nome: Optional[str] = Query(None, min_length=1),
    categoria: Optional[str] = Query(None, min_length=1),
    preco_min: Optional[condecimal(gt=0)] = Query(None),
    preco_max: Optional[condecimal(gt=0)] = Query(None),
    ordenar_por: Optional[str] = Query(None)
):
    # Validação do ordenar_por
    if ordenar_por is not None and ordenar_por not in ALLOWED_ORDER_BY:
        raise HTTPException(status_code=400, detail=f"Parâmetro ordenar_por inválido: {ordenar_por}")

    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

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
        params.append(float(preco_min))
    if preco_max is not None:
        query += " AND preco <= ?"
        params.append(float(preco_max))
    if ordenar_por:
        query += f" ORDER BY {ordenar_por} COLLATE NOCASE"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
    except Error:
        raise HTTPException(status_code=500, detail="Erro interno no servidor")

    produtos = [
        {
            "id": row["id"],
            "nome": row["nome"],
            "categoria": row["categoria"],
            "preco": row["preco"],
            "estoque": row["estoque"],
        }
        for row in rows
    ]

    return produtos