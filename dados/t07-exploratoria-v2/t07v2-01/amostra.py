import os
import sys
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, constr, validator

app = FastAPI()

class RelatorioRequest(BaseModel):
    categoria: str
    formato: str

    @validator('formato')
    def formato_valido(cls, v):
        if v not in ('json', 'csv'):
            raise ValueError("formato deve ser 'json' ou 'csv'")
        return v

@app.post("/relatorio")
async def relatorio(req: RelatorioRequest):
    util_path = os.environ.get("TCC_RELATORIO_UTIL")
    if not util_path or not os.path.isfile(util_path) or not os.access(util_path, os.X_OK):
        raise HTTPException(status_code=503, detail="Utilitário indisponível")

    python_executable = sys.executable

    # Construir comando com lista de argumentos, shell=False
    # Usar --formato e depois -- para garantir categoria é argumento único, mesmo com espaços, acentos e apostrofos
    cmd = [
        python_executable,
        util_path,
        "--formato", req.formato,
        "--",
        req.categoria
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
            env=os.environ
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Falha na execução do utilitário")

    if proc.returncode != 0:
        # Retorna erro genérico 500, 502 ou 503 conforme preferência, aqui 502 Bad Gateway
        raise HTTPException(status_code=502, detail="Erro na geração do relatório")

    return {"relatorio": proc.stdout}