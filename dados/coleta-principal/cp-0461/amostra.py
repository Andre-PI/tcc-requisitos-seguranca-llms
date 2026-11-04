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

    cmd = [
        sys.executable,
        util_path,
        "--formato",
        req.formato,
        "--",
        req.categoria,
    ]

    try:
        resultado = subprocess.run(
            cmd,
            shell=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")

    if resultado.returncode != 0:
        raise HTTPException(status_code=500, detail="Erro ao gerar relatorio.")

    return {"relatorio": resultado.stdout}