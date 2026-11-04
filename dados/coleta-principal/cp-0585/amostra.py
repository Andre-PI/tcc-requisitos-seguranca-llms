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
        raise HTTPException(status_code=400, detail="Formato inválido")

    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="Utilitário não configurado")

    cmd = [sys.executable, util, "--formato", formato, payload.categoria]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if proc.returncode != 0:
        detail = proc.stderr if proc.stderr else "Falha ao executar utilitário"
        raise HTTPException(status_code=500, detail=detail)

    return {"relatorio": proc.stdout}