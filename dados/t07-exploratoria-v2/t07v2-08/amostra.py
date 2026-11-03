import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(min_length=1)
    formato: Literal["json", "csv"]

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("categoria vazia")
        return v


def _obter_caminho_utilitario() -> str:
    caminho = os.environ.get("TCC_RELATORIO_UTIL")
    if not caminho:
        raise HTTPException(status_code=500, detail="Utilitario nao configurado")
    return caminho


def _executar_utilitario(categoria: str, formato: str) -> str:
    util = _obter_caminho_utilitario()
    if not Path(util).is_file():
        raise HTTPException(status_code=500, detail="Utilitario invalido")

    try:
        resultado = subprocess.run(
            [sys.executable, util, "--formato", formato, categoria],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            env={
                **os.environ,
                "PYTHONUNBUFFERED": "1",
            },
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tempo limite excedido")
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao executar utilitario")

    if resultado.returncode != 0:
        detalhe = resultado.stderr.strip() or "Falha ao executar utilitario"
        raise HTTPException(status_code=502, detail=detalhe)

    return resultado.stdout


@app.post("/relatorio", status_code=200)
def relatorio(payload: RelatorioRequest):
    saida = _executar_utilitario(payload.categoria, payload.formato)
    return {"relatorio": saida}