from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import sys
import subprocess
from typing import Literal

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(...)
    formato: Literal["json", "csv"]


@app.post("/relatorio")
def gerar_relatorio(payload: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="TCC_RELATORIO_UTIL nao definido")

    cmd = [sys.executable, util, "--formato", payload.formato, "--", payload.categoria]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=os.environ.copy(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "erro": "utilitario externo falhou",
                "codigo": proc.returncode,
                "stderr": proc.stderr,
                "stdout": proc.stdout,
            },
        )

    return {"relatorio": proc.stdout}