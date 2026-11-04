import os
import subprocess
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class RelatorioRequest(BaseModel):
    categoria: str
    formato: str


app = FastAPI()


@app.post("/relatorio")
def gerar_relatorio(req: RelatorioRequest):
    script_path = os.environ.get("TCC_RELATORIO_UTIL")
    if not script_path:
        raise HTTPException(status_code=500, detail="TCC_RELATORIO_UTIL não configurado")

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
            detail=f"Erro na execução do utilitário: {e.stderr}",
        )