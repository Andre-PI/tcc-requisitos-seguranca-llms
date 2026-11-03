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

    if not util_path or not os.path.isfile(util_path) or not os.access(util_path, os.X_OK):
        raise HTTPException(status_code=500, detail="Utilitário de relatório não configurado corretamente")

    if dados is None or log is None:
        raise HTTPException(status_code=500, detail="Variáveis de ambiente TCC_RELATORIO_DADOS ou TCC_RELATORIO_LOG não definidas")

    env = os.environ.copy()
    env["TCC_RELATORIO_DADOS"] = dados
    env["TCC_RELATORIO_LOG"] = log

    cmd = [sys.executable, util_path, "--formato", req.formato, req.categoria]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao executar utilitário: {e}")

    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Utilitário retornou erro: {proc.stderr.strip()}")

    return {"relatorio": proc.stdout}