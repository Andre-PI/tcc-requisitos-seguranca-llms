import os
import sqlite3
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, Path

from tcc_t06_infra import usuario_atual

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definido")
    return db_path


def _query_one(query: str, params: tuple[Any, ...]) -> tuple[Any, ...] | None:
    conn = sqlite3.connect(_get_db_path())
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, params)
        row = cur.fetchone()
        return tuple(row) if row is not None else None
    finally:
        conn.close()


def _query_all(query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    conn = sqlite3.connect(_get_db_path())
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/pedidos/{id}")
def get_pedido(
    id: int = Path(..., ge=1),
    usuario: dict = Depends(usuario_atual),
):
    pedido = _query_one(
        """
        SELECT id, usuario_id, numero, data, valor_total, status
        FROM pedidos
        WHERE id = ?
        """,
        (id,),
    )

    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    usuario_id = usuario.get("id")
    if pedido[1] != usuario_id:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

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
        "numero": pedido[2],
        "data": pedido[3],
        "status": pedido[5],
        "valor_total": pedido[4],
        "itens": itens,
    }