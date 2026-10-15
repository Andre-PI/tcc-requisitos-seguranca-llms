from fastapi import FastAPI, Query, HTTPException
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
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
def listar_produtos(
    nome: Optional[str] = Query(default=None, min_length=1, max_length=200),
    categoria: Optional[str] = Query(default=None, min_length=1, max_length=100),
    preco_min: Optional[float] = Query(default=None, ge=0),
    preco_max: Optional[float] = Query(default=None, ge=0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

    base_query = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    where_clauses = []
    params = {}

    if nome is not None:
        where_clauses.append("nome LIKE :nome")
        params["nome"] = f"%{nome}%"

    if categoria is not None:
        where_clauses.append("categoria = :categoria")
        params["categoria"] = categoria

    if preco_min is not None:
        where_clauses.append("preco >= :preco_min")
        params["preco_min"] = preco_min

    if preco_max is not None:
        where_clauses.append("preco <= :preco_max")
        params["preco_max"] = preco_max

    query = base_query
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    order_map = {
        "preco": "preco",
        "nome": "nome",
    }
    if ordenar_por is not None:
        query += f" ORDER BY {order_map[ordenar_por]}"

    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [Produto(**dict(row)) for row in rows]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao processar a consulta")