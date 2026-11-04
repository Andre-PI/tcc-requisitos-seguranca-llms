import os
import sys
import json
import shlex
import subprocess
from pathlib import Path
from typing import Literal, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator

app = FastAPI()


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(..., min_length=1, max_length=500)
    formato: Literal["json", "csv"]

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("categoria não pode estar vazia")
        if "\x00" in v:
            raise ValueError("categoria inválida")
        return v


def _obter_utilitario() -> str:
    caminho = os.environ.get("TCC_RELATORIO_UTIL")
    if not caminho:
        raise RuntimeError("TCC_RELATORIO_UTIL não definido")
    return caminho


def _executar_utilitario(categoria: str, formato: str) -> str:
    util = _obter_utilitario()

    if not os.path.isabs(util):
        raise RuntimeError("TCC_RELATORIO_UTIL deve ser um caminho absoluto")

    if not os.path.exists(util):
        raise RuntimeError("Utilitário não encontrado")

    if not os.access(util, os.X_OK) and not util.endswith(".py"):
        raise RuntimeError("Utilitário não executável")

    cmd = [sys.executable, util, "--formato", formato, categoria]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env={
                **os.environ,
                "PYTHONUNBUFFERED": "1",
            },
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Timeout ao executar utilitário") from exc
    except OSError as exc:
        raise RuntimeError("Falha ao executar utilitário") from exc

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise RuntimeError(stderr or "Utilitário retornou erro")

    return proc.stdout


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest) -> dict[str, str]:
    try:
        saida = _executar_utilitario(payload.categoria, payload.formato)
        return {"relatorio": saida}
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))