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
        valor = v.strip().lower()
        if valor not in {"json", "csv"}:
            raise ValueError("formato deve ser json ou csv")
        return valor

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        valor = v.strip()
        if not valor:
            raise ValueError("categoria nao pode ser vazia")
        return valor


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="TCC_RELATORIO_UTIL nao definido")

    cmd = [sys.executable, util, "--formato", payload.formato, payload.categoria]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"falha ao executar utilitario: {exc}")

    if proc.returncode != 0:
        detail = proc.stderr if proc.stderr else proc.stdout
        raise HTTPException(
            status_code=500,
            detail=detail.strip() or "utilitario retornou erro",
        )

    return {"relatorio": proc.stdout}