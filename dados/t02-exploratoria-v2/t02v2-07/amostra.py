import os
import re
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("Variável de ambiente TCC_DB_PATH não definida.")

if not DB_PATH.startswith(("sqlite:////", "sqlite:///")):
    if DB_PATH.startswith("/"):
        DB_URL = f"sqlite:///{DB_PATH}"
    else:
        DB_URL = f"sqlite:///{os.path.abspath(DB_PATH)}"
else:
    DB_URL = DB_PATH

engine = create_engine(
    DB_URL,
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},
)

app = FastAPI(title="Produtos")


class ProdutoOut(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


NomeQuery = Annotated[
    str | None,
    Query(
        default=None,
        min_length=1,
        max_length=200,
        description="Busca parcial por nome",
    ),
]
CategoriaQuery = Annotated[
    str | None,
    Query(
        default=None,
        min_length=1,
        max_length=120,
        description="Categoria exata",
    ),
]
PrecoQuery = Annotated[
    float | None,
    Query(
        default=None,
        ge=0,
        description="Preço mínimo ou máximo",
    ),
]
OrdenarPorQuery = Annotated[
    Literal["preco", "nome"] | None,
    Query(default=None, description="Ordenação crescente por preco ou nome"),
]


def _sanitize_like(value: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(status_code=422, detail="Parâmetro inválido.")
    if len(value) > 200:
        raise HTTPException(status_code=422, detail="Parâmetro inválido.")
    return re.sub(r"([%_\\])", r"\\\1", value)


@app.get("/produtos", response_model=list[ProdutoOut], status_code=200)
def listar_produtos(
    nome: NomeQuery = None,
    categoria: CategoriaQuery = None,
    preco_min: PrecoQuery = None,
    preco_max: PrecoQuery = None,
    ordenar_por: OrdenarPorQuery = None,
):
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(
            status_code=422,
            detail="preco_min não pode ser maior que preco_max.",
        )

    sql = [
        "SELECT id, nome, categoria, preco, estoque",
        "FROM produtos",
    ]
    conditions = []
    params: dict[str, object] = {}

    if nome is not None:
        nome_sanitizado = _sanitize_like(nome)
        conditions.append("nome LIKE :nome ESCAPE '\\'")
        params["nome"] = f"%{nome_sanitizado}%"

    if categoria is not None:
        categoria_sanitizada = categoria.strip()
        if not categoria_sanitizada:
            raise HTTPException(status_code=422, detail="Parâmetro inválido.")
        conditions.append("categoria = :categoria")
        params["categoria"] = categoria_sanitizada

    if preco_min is not None:
        conditions.append("preco >= :preco_min")
        params["preco_min"] = preco_min

    if preco_max is not None:
        conditions.append("preco <= :preco_max")
        params["preco_max"] = preco_max

    if conditions:
        sql.append("WHERE " + " AND ".join(conditions))

    if ordenar_por == "preco":
        sql.append("ORDER BY preco ASC, id ASC")
    elif ordenar_por == "nome":
        sql.append("ORDER BY nome ASC, id ASC")
    else:
        sql.append("ORDER BY id ASC")

    query = text("\n".join(sql))

    try:
        with engine.connect() as conn:
            rows = conn.execute(query, params).mappings().all()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro ao consultar produtos.")

    return [ProdutoOut.model_validate(row) for row in rows]