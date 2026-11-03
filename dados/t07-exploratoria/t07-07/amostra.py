import os
import subprocess
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, constr
from typing import Literal

app = FastAPI()

class RelatorioRequest(BaseModel):
    categoria: str = Field(...)
    formato: Literal["json", "csv"]

@app.post("/relatorio")
async def relatorio(req: RelatorioRequest):
    util_path = os.environ.get("TCC_RELATORIO_UTIL")
    if not util_path or not os.path.isfile(util_path) or not os.access(util_path, os.X_OK):
        raise HTTPException(status_code=503, detail="Serviço indisponível")

    # Comando fixo: [sys.executable, util_path, --formato, formato, --, categoria]
    # Usar sys.executable fixo conforme contrato, aqui usamos os.environ["_"] ou import sys
    import sys

    cmd = [
        sys.executable,
        util_path,
        "--formato",
        req.formato,
        "--",
        req.categoria,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=503, detail="Servico indisponivel")

    if proc.returncode == 0:
        return {"relatorio": proc.stdout}
    elif 1 <= proc.returncode <= 127:
        # erro generico interno
        raise HTTPException(status_code=500, detail="Erro interno no servidor")
    elif proc.returncode >= 128:
        # possivel erro temporario/disponibilidade
        raise HTTPException(status_code=503, detail="Servico indisponivel")
    else:
        # fallback
        raise HTTPException(status_code=502, detail="Erro de gateway")