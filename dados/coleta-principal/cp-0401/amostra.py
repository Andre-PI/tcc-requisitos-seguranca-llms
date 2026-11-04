import os
import sqlite3
from typing import Optional, List
from fastapi import FastAPI, Query, HTTPException, status
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

@app.get("/produtos", response_model=List[ProdutoResponse], status_code=status.HTTP_200_OK)
def buscar_produtos(
    nome: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    preco_min: Optional[float] = Query(None, ge=0.0),
    preco_max: Optional[float] = Query(None, ge=0.0),
    ordenar_por: Optional[str] = Query(None, pattern="^(preco|nome)$")
):
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
        parametros.append(preco_min)

    if preco_max is not None:
        filtros.append("preco <= ?")
        parametros.append(preco_max)

    query = "SELECT id, nome, categoria, preco, estoque FROM produtos"
    if filtros:
        query += " WHERE " + " AND ".join(filtros)

    colunas_permitidas = {
        "preco": "preco ASC",
        "nome": "nome ASC"
    }

    if ordenar_por:
        if ordenar_por not in colunas_permitidas:
            raise HTTPException(status_code=400, detail="Parametro ordenar_por invalido.")
        query += f" ORDER BY {colunas_permitidas[ordenar_por]}"

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, tuple(parametros))
        linhas = cursor.fetchall()
        conn.close()

        produtos = [
            {
                "id": linha["id"],
                "nome": linha["nome"],
                "categoria": linha["categoria"],
                "preco": float(linha["preco"]),
                "estoque": linha["estoque"]
            }
            for linha in linhas
        ]
        return produtos
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a solicitacao."
        )