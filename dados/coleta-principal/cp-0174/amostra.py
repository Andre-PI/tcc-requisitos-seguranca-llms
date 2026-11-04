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
    script_path = os.environ.get("TCC_RELATORIO_UTIL")
    if not script_path:
        raise HTTPException(
            status_code=500, detail="Variavel TCC_RELATORIO_UTIL nao definida"
        )

    cmd = [sys.executable, script_path, "--formato", req.formato, req.categoria]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar o utilitario: {result.stderr}",
        )

    return {"relatorio": result.stdout}