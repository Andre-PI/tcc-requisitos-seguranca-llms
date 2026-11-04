import os
import sys
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(..., min_length=1)
    formato: str = Field(..., min_length=1)

    @field_validator("formato")
    @classmethod
    def validar_formato(cls, v: str) -> str:
        if v not in {"json", "csv"}:
            raise ValueError("formato inválido")
        return v


@app.post("/relatorio")
def relatorio(req: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="erro interno")

    try:
        proc = subprocess.run(
            [sys.executable, util, "--formato", req.formato, "--", req.categoria],
            shell=False,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="erro interno")
    except OSError:
        raise HTTPException(status_code=502, detail="erro interno")

    if proc.returncode != 0:
        raise HTTPException(status_code=502, detail="erro interno")

    return {"relatorio": proc.stdout}