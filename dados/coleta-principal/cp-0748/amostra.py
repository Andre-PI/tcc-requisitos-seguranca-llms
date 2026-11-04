from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
import os
import sys
import subprocess

app = FastAPI()


class RelatorioRequest(BaseModel):
    categoria: str = Field(min_length=1)
    formato: Literal["json", "csv"]


def _obter_utilitario() -> str:
    caminho = os.environ.get("TCC_RELATORIO_UTIL")
    if not caminho:
        raise HTTPException(status_code=500, detail="Erro interno")
    return caminho


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    utilitario = _obter_utilitario()

    cmd = [
        sys.executable,
        utilitario,
        "--formato",
        payload.formato,
        "--",
        payload.categoria,
    ]

    try:
        resultado = subprocess.run(
            cmd,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Serviço indisponível")
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno")

    if resultado.returncode != 0:
        raise HTTPException(status_code=502, detail="Erro ao processar relatório")

    return {"relatorio": resultado.stdout}