import json
import os
import subprocess
import sys
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
        if not v.strip():
            raise ValueError("categoria vazia")
        return v


@app.post("/relatorio")
def relatorio(req: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="TCC_RELATORIO_UTIL nao definido")

    cmd = [sys.executable, util, "--formato", req.formato, req.categoria]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Utilitario nao encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao executar utilitario: {e}")

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "Falha ao executar utilitario"
        raise HTTPException(status_code=500, detail=detail)

    return {"relatorio": proc.stdout}