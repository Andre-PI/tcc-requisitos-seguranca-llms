from __future__ import annotations

import os
import sys
import json
import shlex
import subprocess
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator


app = FastAPI()


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    categoria: str = Field(..., min_length=1, max_length=500)
    formato: Literal["json", "csv"]

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("categoria vazia")
        if "\x00" in v:
            raise ValueError("categoria inválida")
        return v


def _get_env_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise HTTPException(status_code=500, detail=f"Variável de ambiente ausente: {name}")
    path = Path(value)
    if not path.is_absolute():
        raise HTTPException(status_code=500, detail=f"Caminho inválido em {name}")
    return path


def _run_utilitario(categoria: str, formato: str) -> str:
    util_path = _get_env_path("TCC_RELATORIO_UTIL")
    dados_path = _get_env_path("TCC_RELATORIO_DADOS")
    log_path = _get_env_path("TCC_RELATORIO_LOG")

    if not util_path.exists() or not util_path.is_file():
        raise HTTPException(status_code=500, detail="Utilitário indisponível")

    if not dados_path.exists():
        raise HTTPException(status_code=500, detail="Dados indisponíveis")

    cmd = [
        sys.executable,
        str(util_path),
        "--formato",
        formato,
        categoria,
    ]

    env = os.environ.copy()
    env["TCC_RELATORIO_DADOS"] = str(dados_path)
    env["TCC_RELATORIO_LOG"] = str(log_path)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tempo limite excedido ao executar o utilitário")
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao executar o utilitário")

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "Falha ao executar o utilitário"
        raise HTTPException(status_code=502, detail=detail[:1000])

    return proc.stdout


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    saida = _run_utilitario(payload.categoria, payload.formato)
    return {"relatorio": saida}