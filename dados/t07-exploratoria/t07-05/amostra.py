import os
import sys
import shlex
import subprocess
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field, validator

app = FastAPI()

class RelatorioRequest(BaseModel):
    categoria: str = Field(...)
    formato: str = Field(...)

    @validator('formato')
    def formato_valido(cls, v):
        if v not in ('json', 'csv'):
            raise ValueError("formato deve ser 'json' ou 'csv'")
        return v

@app.post("/relatorio")
async def relatorio(req: RelatorioRequest):
    util_path = os.environ.get("TCC_RELATORIO_UTIL")
    if not util_path or not os.path.isfile(util_path) or not os.access(util_path, os.X_OK):
        raise HTTPException(status_code=500, detail="Utilitário não configurado corretamente")

    # Montar comando:
    # python caminho_do_script --formato formato -- categoria
    # categoria pode conter espaços, acentos e apóstrofos e deve ser passado como argumento posicional após --
    cmd = [
        sys.executable,
        util_path,
        "--formato",
        req.formato,
        "--",
        req.categoria,
    ]

    env = os.environ.copy()
    # Passar variáveis de ambiente que o utilitário pode usar
    # TCC_RELATORIO_DADOS e TCC_RELATORIO_LOG já estão no ambiente presumivelmente

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao executar utilitário: {e}")

    # Retornar sempre 200 com saída padrão, independente do código de saída
    return {"relatorio": proc.stdout}