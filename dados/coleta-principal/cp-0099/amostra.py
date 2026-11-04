import os
import sys
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI()


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria: str = Field(min_length=1)
    formato: str = Field(min_length=1)


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="TCC_RELATORIO_UTIL nao definido")

    cmd = [sys.executable, util, "--formato", payload.formato, payload.categoria]

    env = os.environ.copy()
    for key in ("TCC_RELATORIO_DADOS", "TCC_RELATORIO_LOG"):
        if key in os.environ:
            env[key] = os.environ[key]

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
        detail = proc.stderr.strip() or proc.stdout.strip() or "Utilitario retornou erro"
        raise HTTPException(status_code=500, detail=detail)

    return {"relatorio": proc.stdout}