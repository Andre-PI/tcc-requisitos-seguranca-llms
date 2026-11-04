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


@app.post("/relatorio")
def criar_relatorio(req: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="TCC_RELATORIO_UTIL nao definido")

    cmd = [sys.executable, util, "--formato", req.formato, req.categoria]

    env = os.environ.copy()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao executar utilitario: {exc}") from exc

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"Utilitario retornou codigo {proc.returncode}"
        raise HTTPException(status_code=500, detail=detail)

    return {"relatorio": proc.stdout}