import os
import subprocess
import sys
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str
    formato: Literal["json", "csv"]


@app.post("/relatorio")
def gerar_relatorio(req: RelatorioRequest):
    util_script = os.environ.get("TCC_RELATORIO_UTIL")
    if not util_script:
        raise HTTPException(
            status_code=500, detail="Variavel TCC_RELATORIO_UTIL nao definida"
        )

    cmd = [sys.executable, util_script, "--formato", req.formato, req.categoria]

    resultado = subprocess.run(cmd, capture_output=True, text=True)

    if resultado.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar utilitario: {resultado.stderr}",
        )

    return {"relatorio": resultado.stdout}