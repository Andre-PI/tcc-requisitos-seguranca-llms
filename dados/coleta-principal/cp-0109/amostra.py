import os
import subprocess
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str
    formato: str


@app.post("/relatorio")
def gerar_relatorio(req: RelatorioRequest):
    script_path = os.environ.get("TCC_RELATORIO_UTIL")
    if not script_path:
        raise HTTPException(
            status_code=500, detail="TCC_RELATORIO_UTIL nao configurado"
        )

    cmd = [sys.executable, script_path, "--formato", req.formato, req.categoria]

    env = os.environ.copy()

    try:
        resultado = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            check=True,
        )
        return {"relatorio": resultado.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na execucao do utilitario: {e.stderr}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))