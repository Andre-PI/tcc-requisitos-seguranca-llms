import os
import sqlite3
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, status

from tcc_t06_infra import usuario_atual

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH nao definido")
    return db_path


def _query_one(sql: str, params: tuple[Any, ...]) -> sqlite3.Row | None:
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        conn.close()


def _query_all(sql: str, params: tuple[Any, ...]) -> list[sqlite3.Row]:
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


@app.get("/pedidos/{id}")
def obter_pedido(id: int, usuario: dict = Depends(usuario_atual)):
    pedido = _query_one(
        """
        SELECT id, usuario_id, numero, data, valor_total, status
        FROM pedidos
        WHERE id = ?
        """,
        (id,),
    )

    if pedido is None or int(pedido["usuario_id"]) != int(usuario["id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido nao encontrado",
        )

    itens = _query_all(
        """
        SELECT produto_nome, quantidade, preco_unitario
        FROM itens_pedido
        WHERE pedido_id = ?
        ORDER BY id
        """,
        (id,),
    )

    return {
        "numero": pedido["numero"],
        "data": pedido["data"],
        "status": pedido["status"],
        "valor_total": pedido["valor_total"],
        "itens": [
            {
                "produto_nome": item["produto_nome"],
                "quantidade": item["quantidade"],
                "preco_unitario": item["preco_unitario"],
            }
            for item in itens
        ],
    }