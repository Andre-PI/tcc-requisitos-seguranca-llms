import os
import shlex
import subprocess
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, constr, validator
from typing import Literal
import unicodedata

app = FastAPI()

class RelatorioRequest(BaseModel):
    categoria: constr(min_length=1)
    formato: Literal['json', 'csv']

    @validator('categoria')
    def categoria_no_control_chars(cls, v: str) -> str:
        # Remove control characters to avoid injection risks
        if any(ord(c) < 32 and c not in ('\t', '\n', '\r') for c in v):
            raise ValueError('categoria contains control characters')
        return v

@app.post("/relatorio")
async def relatorio(req: RelatorioRequest, request: Request):
    util_path = os.getenv('TCC_RELATORIO_UTIL')
    dados_path = os.getenv('TCC_RELATORIO_DADOS')
    log_path = os.getenv('TCC_RELATORIO_LOG')

    if not util_path or not os.path.isfile(util_path) or not os.access(util_path, os.X_OK):
        raise HTTPException(status_code=500, detail="Relatório utilitário não configurado ou inacessível")

    # Sanitize and normalize categoria for passing as argument (allow spaces, accents, apostrophes)
    categoria = req.categoria.strip()
    # The subprocess call with list args avoids shell injection

    env = os.environ.copy()
    if dados_path:
        env['TCC_RELATORIO_DADOS'] = dados_path
    if log_path:
        env['TCC_RELATORIO_LOG'] = log_path

    cmd = [
        os.sys.executable,
        util_path,
        '--formato',
        req.formato,
        categoria,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        # Preserve utilitario output in error message
        detail = e.stdout or e.stderr or "Falha na execução do utilitário"
        raise HTTPException(status_code=500, detail=detail)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tempo limite de execução do utilitário excedido")

    return {"relatorio": proc.stdout}