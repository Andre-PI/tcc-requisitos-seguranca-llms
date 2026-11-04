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
    if not script_path or not os.path.exists(script_path):
        raise HTTPException(
            status_code=500, detail="Configuração do utilitário não encontrada ou inválida."
        )

    cmd = [
        sys.executable,
        script_path,
        "--formato",
        req.formato.value,
        req.categoria,
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar o utilitário de relatório: {e.stderr.strip()}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro inesperado durante o processamento: {str(e)}"
        )

    return {"relatorio": result.stdout}