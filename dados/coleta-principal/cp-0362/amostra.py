from __future__ import annotations

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
        v = v.strip()
        if not v:
            raise ValueError("categoria não pode ser vazia")
        return v


class RelatorioResponse(BaseModel):
    relatorio: str


@app.post("/relatorio", response_model=RelatorioResponse)
def gerar_relatorio(req: RelatorioRequest) -> RelatorioResponse:
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="TCC_RELATORIO_UTIL não definido")

    cmd = [sys.executable, util, "--formato", req.formato, req.categoria]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao executar utilitário: {exc}") from exc

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "utilitário retornou erro"
        raise HTTPException(status_code=500, detail=detail)

    return RelatorioResponse(relatorio=proc.stdout)