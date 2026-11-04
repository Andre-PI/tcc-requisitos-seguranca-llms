import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(..., min_length=1)
    formato: Literal["json", "csv"]

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("categoria inválida")
        valor = v.strip()
        if not valor:
            raise ValueError("categoria inválida")
        if "\x00" in valor:
            raise ValueError("categoria inválida")
        return valor


def _obter_ambiente_seguro() -> dict[str, str]:
    env = os.environ.copy()
    for chave in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
        env.pop(chave, None)
    return env


def _validar_caminho_utilitario() -> str:
    util = os.getenv("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="Utilitário não configurado")
    caminho = Path(util)
    if not caminho.is_file():
        raise HTTPException(status_code=500, detail="Utilitário inválido")
    return str(caminho)


def _executar_utilitario(categoria: str, formato: str) -> str:
    util = _validar_caminho_utilitario()
    cmd = [sys.executable, util, "--formato", formato, categoria]

    try:
        resultado = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_obter_ambiente_seguro(),
            check=False,
        )
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao executar o utilitário")

    if resultado.returncode != 0:
        raise HTTPException(status_code=502, detail="Utilitário retornou erro")

    return resultado.stdout


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    saida = _executar_utilitario(payload.categoria, payload.formato)
    return {"relatorio": saida}