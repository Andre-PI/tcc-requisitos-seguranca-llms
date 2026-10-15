from fastapi import FastAPI, Query, HTTPException
from typing import Optional, List, Literal
import sqlite3

app = FastAPI()

DATABASE = "app.db"

ALLOWED_ORDER_BY = {
    "preco": "preco",
    "nome": "nome",
}


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/produtos")
def buscar_produtos(
    nome: Optional[str] = Query(default=None, min_length=1, max_length=200),
    categoria: Optional[str] = Query(default=None, min_length=1, max_length=100),
    preco_min: Optional[float] = Query(default=None, ge=0),
    preco_max: Optional[float] = Query(default=None, ge=0),
    ordenar_por: Optional[Literal["preco", "nome"]] = Query(default=None),
):
    try:
        if preco_min is not None and preco_max is not None and preco_min > preco_max:
            raise HTTPException(status_code=400, detail="preco_min não pode ser maior que preco_max")

        sql = """
            SELECT id, nome, categoria, preco, estoque
            FROM produtos
            WHERE 1=1
        """
        params = []

        if nome is not None:
            sql += " AND nome LIKE ?"
            params.append(f"%{nome}%")

        if categoria is not None:
            sql += " AND categoria = ?"
            params.append(categoria)

        if preco_min is not None:
            sql += " AND preco >= ?"
            params.append(preco_min)

        if preco_max is not None:
            sql += " AND preco <= ?"
            params.append(preco_max)

        if ordenar_por is not None:
            order_col = ALLOWED_ORDER_BY.get(ordenar_por)
            if order_col is None:
                raise HTTPException(status_code=400, detail="ordenar_por inválido")
            sql += f" ORDER BY {order_col}"

        with get_db_connection() as conn:
            cursor = conn.execute(sql, params)
            produtos = [dict(row) for row in cursor.fetchall()]

        return {"produtos": produtos}

    except HTTPException:
        raise
    except (sqlite3.Error, ValueError, TypeError):
        raise HTTPException(status_code=500, detail="Erro interno ao consultar produtos")