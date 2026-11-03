import os
import sys
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

class RelatorioRequest(BaseModel):
    categoria: str = Field(..., min_length=1)
    formato: str = Field(..., regex="^(json|csv)$")

@app.post("/relatorio")
async def gerar_relatorio(req: RelatorioRequest):
    util_path = os.getenv("TCC_RELATORIO_UTIL")
    dados = os.getenv("TCC_RELATORIO_DADOS")
    log = os.getenv("TCC_RELATORIO_LOG")

    if not util_path:
        raise HTTPException(status_code=500, detail="Variável TCC_RELATORIO_UTIL não definida")
    if not dados:
        raise HTTPException(status_code=500, detail="Variável TCC_RELATORIO_DADOS não definida")
    if not log:
        raise HTTPException(status_code=500, detail="Variável TCC_RELATORIO_LOG não definida")

    cmd = [
        sys.executable,
        util_path,
        "--formato", req.formato,
        "--",
        req.categoria,
    ]

    env = os.environ.copy()
    env["TCC_RELATORIO_DADOS"] = dados
    env["TCC_RELATORIO_LOG"] = log

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Tempo de execução do utilitário excedido")

    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {proc.stderr.strip()}")

    return {"relatorio": proc.stdout}