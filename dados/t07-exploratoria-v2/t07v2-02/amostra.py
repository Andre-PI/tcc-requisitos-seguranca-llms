import os
import sys
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(..., min_length=1)
    formato: str = Field(..., min_length=1)


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    formato = payload.formato.strip().lower()
    if formato not in {"json", "csv"}:
        raise HTTPException(status_code=400, detail="formato inválido")

    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="utilitário não configurado")

    cmd = [sys.executable, util, "--formato", formato, payload.categoria]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"falha ao executar utilitário: {e}") from e

    if proc.returncode != 0:
        detail = proc.stderr if proc.stderr else proc.stdout
        raise HTTPException(status_code=500, detail=detail.strip() or "erro ao executar utilitário")

    return {"relatorio": proc.stdout}