import os
import sys
import subprocess
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(..., min_length=1)
    formato: Literal["json", "csv"]


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        return {"relatorio": ""}

    cmd = [sys.executable, util, "--formato", payload.formato, payload.categoria]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    return {"relatorio": proc.stdout}