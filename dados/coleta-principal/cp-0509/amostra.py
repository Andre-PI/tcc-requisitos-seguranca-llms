import os
import sys
import subprocess
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict


app = FastAPI()


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(min_length=1, max_length=5000)
    formato: Literal["json", "csv"]


def _run_utilitario(categoria: str, formato: str) -> str:
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="Utilitário não configurado")

    util_path = Path(util)
    if not util_path.is_absolute():
        raise HTTPException(status_code=500, detail="Caminho do utilitário inválido")

    if not util_path.exists() or not util_path.is_file():
        raise HTTPException(status_code=500, detail="Utilitário indisponível")

    cmd = [sys.executable, str(util_path), "--formato", formato, categoria]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tempo limite excedido")
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao executar utilitário")

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "Falha ao gerar relatório"
        raise HTTPException(status_code=502, detail=detail)

    return completed.stdout


@app.post("/relatorio", status_code=200)
def relatorio(payload: RelatorioRequest):
    texto = _run_utilitario(payload.categoria, payload.formato)
    return {"relatorio": texto}