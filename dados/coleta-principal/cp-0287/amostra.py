import os
import sys
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(...)
    formato: str = Field(...)

    @field_validator("formato")
    @classmethod
    def validar_formato(cls, v: str) -> str:
        if v not in {"json", "csv"}:
            raise ValueError("formato inválido")
        return v


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=503, detail="Serviço indisponível")

    try:
        proc = subprocess.run(
            [sys.executable, util, "--formato", payload.formato, "--", payload.categoria],
            shell=False,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Serviço indisponível")
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno")

    if proc.returncode != 0:
        if proc.returncode in {1, 2, 126, 127}:
            raise HTTPException(status_code=502, detail="Falha ao gerar relatório")
        raise HTTPException(status_code=500, detail="Erro interno")

    return {"relatorio": proc.stdout}