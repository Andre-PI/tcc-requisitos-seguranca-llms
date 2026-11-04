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

    env = os.environ.copy()

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            check=True,
        )
        return {"relatorio": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na execucao do utilitario: {e.stderr}",
        )