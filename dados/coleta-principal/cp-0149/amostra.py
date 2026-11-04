from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

app = FastAPI(title="Relatório de Produtos por Categoria")


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(min_length=1)
    formato: Literal["json", "csv"]

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("categoria não pode ser vazia")
        return v


class RelatorioResponse(BaseModel):
    relatorio: str


def _obter_ambiente() -> tuple[Path, dict[str, str]]:
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="Utilitário não configurado")

    util_path = Path(util)
    if not util_path.is_file():
        raise HTTPException(status_code=500, detail="Utilitário inválido")

    env = os.environ.copy()
    return util_path, env


def _executar_utilitario(categoria: str, formato: str) -> str:
    util_path, env = _obter_ambiente()

    cmd = [
        sys.executable,
        str(util_path),
        "--formato",
        formato,
        categoria,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=env,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tempo limite excedido ao gerar relatório")
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao executar utilitário")

    if proc.returncode != 0:
        detail = proc.stderr.strip() or "Falha ao gerar relatório"
        raise HTTPException(status_code=502, detail=detail)

    return proc.stdout


@app.post("/relatorio", response_model=RelatorioResponse)
def relatorio(req: RelatorioRequest) -> RelatorioResponse:
    saida = _executar_utilitario(req.categoria, req.formato)
    return RelatorioResponse(relatorio=saida)