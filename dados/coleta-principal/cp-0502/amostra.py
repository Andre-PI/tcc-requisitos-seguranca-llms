import os
import subprocess
import sys
from fastapi import FastAPI
from pydantic import BaseModel, Literal

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str
    formato: Literal["json", "csv"]


@app.post("/relatorio")
def gerar_relatorio(req: RelatorioRequest):
    script_path = os.environ["TCC_RELATORIO_UTIL"]

    cmd = [
        sys.executable,
        script_path,
        "--formato",
        req.formato,
        req.categoria,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )

    return {"relatorio": result.stdout}