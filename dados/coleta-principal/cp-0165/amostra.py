import os
import sys
import subprocess
from pathlib import Path
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
            raise ValueError("formato invalido")
        return v


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="erro interno")

    util_path = Path(util)
    if not util_path.is_absolute():
        raise HTTPException(status_code=500, detail="erro interno")

    cmd = [sys.executable, str(util_path), "--formato", payload.formato, "--", payload.categoria]

    try:
        proc = subprocess.run(
            cmd,
            shell=False,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        raise HTTPException(status_code=503, detail="erro interno")

    if proc.returncode != 0:
        raise HTTPException(status_code=502, detail="erro interno")

    return {"relatorio": proc.stdout}