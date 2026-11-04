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
    if not util_path or not os.path.exists(util_path):
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")

    cmd = [
        sys.executable,
        util_path,
        f"--formato={req.formato}",
        "--",
        req.categoria,
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            check=False,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")

    if result.returncode != 0:
        raise HTTPException(status_code=502, detail="Falha ao processar o relatorio.")

    return {"relatorio": result.stdout}