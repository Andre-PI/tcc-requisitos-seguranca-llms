import os
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()


def _get_db_path() -> str:
    db_path = os.getenv("TCC_DB_PATH")
    if not db_path:
        raise RuntimeError("TCC_DB_PATH não definida")
    return db_path


def _create_engine() -> Engine:
    db_path = _get_db_path()
    return create_engine(f"sqlite+pysqlite:///{db_path}", future=True)


engine = _create_engine()


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    estoque: int


class ProdutoQueryParams(BaseModel):
    nome: Optional[str] = None
    categoria: Optional[str] = None
    preco_min: Optional[Decimal] = Field(default=None, ge=0)
    preco_max: Optional[Decimal] = Field(default=None, ge=0)
    ordenar_por: Optional[str] = None

    @field_validator("nome", "categoria")
    @classmethod
    def validate_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        return v if v else None

    @field_validator("ordenar_por")
    @classmethod
    def validate_order(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        allowed = {"preco", "nome"}
        if v not in allowed:
            raise ValueError("ordenar_por inválido")
        return v

    @field_validator("preco_max")
    @classmethod
    def validate_preco_max(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("preco_max deve ser >= 0")
        return v

    @field_validator("preco_min")
    @classmethod
    def validate_preco_min(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("preco_min deve ser >= 0")
        return v


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(
    nome: Annotated[Optional[str], Query(default=None)] = None,
    categoria: Annotated[Optional[str], Query(default=None)] = None,
    preco_min: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    preco_max: Annotated[Optional[float], Query(default=None, ge=0)] = None,
    ordenar_por: Annotated[Optional[str], Query(default=None)] = None,
):
    try:
        params = ProdutoQueryParams(
            nome=nome,
            categoria=categoria,
            preco_min=Decimal(str(preco_min)) if preco_min is not None else None,
            preco_max=Decimal(str(preco_max)) if preco_max is not None else None,
            ordenar_por=ordenar_por,
        )

        if params.preco_min is not None and params.preco_max is not None and params.preco_min > params.preco_max:
            raise HTTPException(status_code=422, detail="preco_min não pode ser maior que preco_max")

        sql = "SELECT id, nome, categoria, preco, estoque FROM produtos"
        where_clauses = []
        bind_params = {}

        if params.nome is not None:
            where_clauses.append("nome LIKE :nome")
            bind_params["nome"] = f"%{params.nome}%"
        if params.categoria is not None:
            where_clauses.append("categoria = :categoria")
            bind_params["categoria"] = params.categoria
        if params.preco_min is not None:
            where_clauses.append("preco >= :preco_min")
            bind_params["preco_min"] = float(params.preco_min)
        if params.preco_max is not None:
            where_clauses.append("preco <= :preco_max")
            bind_params["preco_max"] = float(params.preco_max)

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        order_map = {
            "preco": "preco ASC",
            "nome": "nome ASC",
        }
        if params.ordenar_por is not None:
            sql += f" ORDER BY {order_map[params.ordenar_por]}"

        with engine.connect() as conn:
            result = conn.execute(text(sql), bind_params)
            rows = result.mappings().all()

        return [ProdutoOut(**row) for row in rows]

    except HTTPException:
        raise
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Parâmetros inválidos")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno do servidor")