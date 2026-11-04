import os
import subprocess
import sys
from enum import Enum
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()


class FormatoEnum(str, Enum):
    json = "json"
    csv = "csv"


class RelatorioRequest(BaseModel):
    categoria: str = Field(..., min_length=1)
    formato: FormatoEnum


class RelatorioResponse(BaseModel):
    relatorio: str


@app.post("/relatorio", response_model=RelatorioResponse, status_code=200)
def gerar_relatorio(req: RelatorioRequest):
    script_path = os.environ.get("TCC_RELATORIO_UTIL")
    if not script_path or not os.path.isfile(script_path):
        raise HTTPException(status_code=500, detail="Utilitário de relatório não configurado.")

    cmd = [
        sys.executable,
        script_path,
        "--formato",
        req.formato.value,
        req.categoria,
    ]

    env = os.environ.copy()

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            shell=False,
            check=False,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao executar o utilitário.") from e

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail="Falha na geração do relatório.")

    return RelatorioResponse(relatorio=result.stdout)