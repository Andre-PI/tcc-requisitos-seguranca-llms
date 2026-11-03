import os
import sys
import json
import subprocess
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict


app = FastAPI()


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria: str = Field(min_length=1)
    formato: Literal["json", "csv"]


def _executar_utilitario(categoria: str, formato: str) -> str:
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="Utilitario nao configurado")

    if not os.path.isabs(util):
        raise HTTPException(status_code=500, detail="Caminho do utilitario invalido")

    cmd = [sys.executable, util, "--formato", formato, "--", categoria]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=os.environ.copy(),
        )
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao executar utilitario")

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "Utilitario retornou erro"
        raise HTTPException(status_code=502, detail=detail)

    return proc.stdout


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    saida = _executar_utilitario(payload.categoria, payload.formato)
    return {"relatorio": saida}