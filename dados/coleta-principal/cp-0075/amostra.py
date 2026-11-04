import os
import sys
import subprocess
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI()


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria: str = Field(min_length=1)
    formato: Literal["json", "csv"]


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=503, detail="Serviço indisponível")

    cmd = [
        sys.executable,
        util,
        "--formato",
        payload.formato,
        "--",
        payload.categoria,
    ]

    try:
        proc = subprocess.run(
            cmd,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        raise HTTPException(status_code=503, detail="Serviço indisponível")

    if proc.returncode != 0:
        raise HTTPException(status_code=502, detail="Erro ao processar relatório")

    return {"relatorio": proc.stdout}