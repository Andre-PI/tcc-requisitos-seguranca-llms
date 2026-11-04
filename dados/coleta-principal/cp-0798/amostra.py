import os
import subprocess
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str
    formato: str

    @field_validator("formato")
    @classmethod
    def validar_formato(cls, v: str) -> str:
        if v not in ("json", "csv"):
            raise ValueError("O formato deve ser 'json' ou 'csv'")
        return v


class RelatorioResponse(BaseModel):
    relatorio: str


@app.post("/relatorio", response_model=RelatorioResponse, status_code=200)
def gerar_relatorio(req: RelatorioRequest):
    script_path = os.environ.get("TCC_RELATORIO_UTIL")
    if not script_path:
        raise HTTPException(
            status_code=500, detail="TCC_RELATORIO_UTIL não configurado"
        )

    cmd = [
        sys.executable,
        script_path,
        "--formato",
        req.formato,
        req.categoria,
    ]

    resultado = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )

    if resultado.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=resultado.stderr or "Erro ao executar o utilitário de relatório",
        )

    return RelatorioResponse(relatorio=resultado.stdout)