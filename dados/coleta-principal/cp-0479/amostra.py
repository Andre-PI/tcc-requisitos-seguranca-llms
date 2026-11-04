import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator

app = FastAPI(title="Relatorio de Produtos por Categoria")


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(..., min_length=1)
    formato: Literal["json", "csv"]

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        valor = v.strip()
        if not valor:
            raise ValueError("categoria vazia")
        if "\x00" in valor:
            raise ValueError("categoria invalida")
        return valor


def _obter_utilitario() -> str:
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="Utilitário não configurado")
    p = Path(util)
    if not p.is_file():
        raise HTTPException(status_code=500, detail="Utilitário inválido")
    return str(p)


def _executar_utilitario(categoria: str, formato: str) -> str:
    util = _obter_utilitario()

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    try:
        proc = subprocess.run(
            [sys.executable, util, "--formato", formato, categoria],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tempo limite excedido")
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao executar utilitário")

    if proc.returncode != 0:
        detail = proc.stderr.strip() or "Falha ao gerar relatório"
        raise HTTPException(status_code=502, detail=detail[:1000])

    return proc.stdout


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    saida = _executar_utilitario(payload.categoria, payload.formato)
    return {"relatorio": saida}