import os
import subprocess
import sys
from typing import Literal
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(..., min_length=1)
    formato: Literal["json", "csv"]


class RelatorioResponse(BaseModel):
    relatorio: str


@app.post(
    "/relatorio",
    response_model=RelatorioResponse,
    status_code=status.HTTP_200_OK,
)
def gerar_relatorio(payload: RelatorioRequest):
    script_path = os.environ.get("TCC_RELATORIO_UTIL")
    if not script_path or not os.path.isfile(script_path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Utilitario de relatorio nao configurado ou nao encontrado.",
        )

    env = os.environ.copy()

    cmd = [
        sys.executable,
        script_path,
        "--formato",
        payload.formato,
        payload.categoria,
    ]

    try:
        resultado = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            check=False,
            env=env,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar o utilitario: {str(e)}",
        )

    if resultado.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha na execucao do utilitario: {resultado.stderr.strip()}",
        )

    return {"relatorio": resultado.stdout}