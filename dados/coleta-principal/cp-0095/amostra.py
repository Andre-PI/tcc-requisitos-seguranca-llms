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
    util_path = os.environ.get("TCC_RELATORIO_UTIL")
    if not util_path or not os.path.isfile(util_path):
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")

    cmd = [sys.executable, util_path, "--formato", req.formato, "--", req.categoria]

    try:
        resultado = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            check=False,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno no processamento.")

    if resultado.returncode != 0:
        raise HTTPException(status_code=502, detail="Falha na geracao do relatorio.")

    return {"relatorio": resultado.stdout}