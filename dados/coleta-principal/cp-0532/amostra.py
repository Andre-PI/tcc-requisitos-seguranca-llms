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
def gerar_relatorio(req: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="TCC_RELATORIO_UTIL nao definido")

    if req.formato not in {"json", "csv"}:
        raise HTTPException(status_code=400, detail="formato invalido")

    cmd = [sys.executable, util, "--formato", req.formato, req.categoria]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=os.environ.copy(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"falha ao executar utilitario: {exc}") from exc

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=(proc.stderr.strip() or proc.stdout.strip() or "utilitario retornou erro"),
        )

    return {"relatorio": proc.stdout}