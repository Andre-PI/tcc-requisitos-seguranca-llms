import os
import sys
import subprocess
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(min_length=1)
    formato: Literal["json", "csv"]


class RelatorioResponse(BaseModel):
    relatorio: str


@app.post("/relatorio", response_model=RelatorioResponse)
def relatorio(payload: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="TCC_RELATORIO_UTIL não definido")

    cmd = [sys.executable, util, "--formato", payload.formato, payload.categoria]

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
        detail = proc.stderr if proc.stderr else proc.stdout
        raise HTTPException(
            status_code=500,
            detail=detail.strip() if detail else "Utilitário retornou erro",
        )

    return {"relatorio": proc.stdout}