from fastapi import FastAPI, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel, condecimal, constr, validator
import sqlite3
import decimal

app = FastAPI()

class Produto(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: decimal.Decimal
    estoque: int

class ProdutosResponse(BaseModel):
    produtos: List[Produto]

VALID_ORDERS = {"preco", "nome"}

def get_db_connection():
    conn = sqlite3.connect("produtos.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/produtos", response_model=List[Produto])
def busca_produtos(
    nome: Optional[str] = Query(None, min_length=1),
    categoria: Optional[str] = Query(None, min_length=1),
    preco_min: Optional[condecimal(ge=0)] = Query(None),
    preco_max: Optional[condecimal(ge=0)] = Query(None),
    ordenar_por: Optional[str] = Query(None)
):
    if ordenar_por is not None and ordenar_por not in VALID_ORDERS:
        raise HTTPException(status_code=400, detail=f"Parâmetro ordenar_por inválido. Valores permitidos: {', '.join(VALID_ORDERS)}")

    if preco_min is not None and preco_max is not None:
        if preco_min > preco_max:
            raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

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

    if ordenar_por is not None:
        query += f" ORDER BY {ordenar_por} COLLATE NOCASE"

    try:
        conn = get_db_connection()
        cursor = conn.execute(query, parametros)
        rows = cursor.fetchall()
        conn.close()
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar os produtos")

    produtos = [Produto(
        id=row["id"],
        nome=row["nome"],
        categoria=row["categoria"],
        preco=decimal.Decimal(str(row["preco"])),
        estoque=row["estoque"]
    ) for row in rows]

    return produtos