from fastapi import FastAPI, Query, HTTPException
from typing import Optional, List
from pydantic import condecimal, constr, validator
from decimal import Decimal
import sqlite3
import logging

app = FastAPI()

ALLOWED_ORDER_BY = {"preco", "nome"}

class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: Decimal
    estoque: int

@app.get("/produtos", response_model=List[Produto])
def buscar_produtos(
    nome: Optional[str] = Query(None, min_length=1),
    categoria: Optional[str] = Query(None, min_length=1),
    preco_min: Optional[condecimal(ge=0)] = None,
    preco_max: Optional[condecimal(ge=0)] = None,
    ordenar_por: Optional[str] = Query(None)
):
    if ordenar_por is not None and ordenar_por not in ALLOWED_ORDER_BY:
        raise HTTPException(status_code=400, detail="Parâmetro 'ordenar_por' inválido")

    query = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    filtros = []
    parametros = []

    if nome is not None:
        filtros.append("nome LIKE ?")
        parametros.append(f"%{nome}%")
    if categoria is not None:
        filtros.append("categoria = ?")
        parametros.append(categoria)
    if preco_min is not None:
        filtros.append("preco >= ?")
        parametros.append(float(preco_min))
    if preco_max is not None:
        filtros.append("preco <= ?")
        parametros.append(float(preco_max))

    if filtros:
        query += " WHERE " + " AND ".join(filtros)

    if ordenar_por:
        query += f" ORDER BY {ordenar_por}"

    try:
        conn = sqlite3.connect("produtos.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, parametros)
        rows = cursor.fetchall()
        conn.close()
    except Exception:
        logging.exception("Erro ao acessar o banco de dados")
        raise HTTPException(status_code=500, detail="Erro interno no servidor")

    produtos = [
        Produto(
            id=row["id"],
            nome=row["nome"],
            categoria=row["categoria"],
            preco=Decimal(row["preco"]),
            estoque=row["estoque"],
        )
        for row in rows
    ]

    return produtos