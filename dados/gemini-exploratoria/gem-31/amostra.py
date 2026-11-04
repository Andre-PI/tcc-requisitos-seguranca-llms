import os
import sqlite3
from typing import Optional, List
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field

DB_PATH = os.environ.get("TCC_DB_PATH", "produtos.db")

app = FastAPI()

class ProdutoResponse(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int

    class Config:
        from_attributes = True

ALLOWED_ORDER_COLUMNS = {
    "preco": "preco",
    "nome": "nome"
}

@app.get("/produtos", response_model=List[ProdutoResponse])
def get_produtos(
    nome: Optional[str] = Query(None, min_length=1),
    categoria: Optional[str] = Query(None, min_length=1),
    preco_min: Optional[float] = Query(None, ge=0.0),
    preco_max: Optional[float] = Query(None, ge=0.0),
    ordenar_por: Optional[str] = Query(None, regex="^(preco|nome)$")
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min nao pode ser maior que preco_max")

    query = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    conditions = []
    params = []

    if nome is not None:
        conditions.append("nome LIKE ?")
        params.append(f"%{nome}%")

    if categoria is not None:
        conditions.append("categoria = ?")
        params.append(categoria)

    if preco_min is not None:
        conditions.append("preco >= ?")
        params.append(preco_min)

    if preco_max is not None:
        conditions.append("preco <= ?")
        params.append(preco_max)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    if ordenar_por:
        column_name = ALLOWED_ORDER_COLUMNS.get(ordenar_por)
        if not column_name:
            raise HTTPException(status_code=400, detail="Parametro ordenar_por invalido")
        query += f" ORDER BY {column_name} ASC"

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        produtos = [
            {
                "id": row["id"],
                "nome": row["nome"],
                "categoria": row["categoria"],
                "preco": float(row["preco"]),
                "estoque": int(row["estoque"]),
            }
            for row in rows
        ]
        cursor.close()
        conn.close()
        return produtos
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao consultar o banco de dados")