import os
import subprocess
import sys
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str
    formato: str


@app.post("/relatorio")
def gerar_relatorio(req: RelatorioRequest):
    script_path = os.environ["TCC_RELATORIO_UTIL"]

    cmd = [sys.executable, script_path, "--formato", req.formato, req.categoria]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )

    return {"relatorio": result.stdout}