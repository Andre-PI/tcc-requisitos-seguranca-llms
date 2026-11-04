import json
import os
import subprocess
import sys
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(min_length=1)
    formato: Literal["json", "csv"]

    @field_validator("categoria")
    @classmethod
    def validate_categoria(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("categoria inválida")
        value = v.strip()
        if not value:
            raise ValueError("categoria inválida")
        if "\x00" in value:
            raise ValueError("categoria inválida")
        return value


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="Utilitário não configurado")

    if not os.path.isabs(util):
        raise HTTPException(status_code=500, detail="Caminho do utilitário inválido")

    if not os.path.exists(util) or not os.path.isfile(util):
        raise HTTPException(status_code=500, detail="Utilitário não encontrado")

    cmd = [sys.executable, util, "--formato", payload.formato, payload.categoria]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tempo limite excedido")
    except Exception:
        raise HTTPException(status_code=500, detail="Falha ao executar utilitário")

    if completed.returncode != 0:
        raise HTTPException(status_code=500, detail="Falha ao gerar relatório")

    return {"relatorio": completed.stdout}