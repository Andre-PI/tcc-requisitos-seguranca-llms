from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict
import os
import sys
import subprocess
from pathlib import Path


app = FastAPI()


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria: str = Field(min_length=1)
    formato: str = Field(min_length=1)


def _validar_formato(formato: str) -> str:
    valor = formato.strip().lower()
    if valor not in {"json", "csv"}:
        raise HTTPException(status_code=400, detail="Formato inválido")
    return valor


def _obter_utilitario() -> str:
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise HTTPException(status_code=500, detail="Utilitário indisponível")
    return util


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    formato = _validar_formato(payload.formato)
    categoria = payload.categoria

    util = _obter_utilitario()

    try:
        resultado = subprocess.run(
            [sys.executable, util, "--formato", formato, categoria],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tempo limite excedido")
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao executar utilitário")

    if resultado.returncode != 0:
        detail = resultado.stderr.strip() or "Falha ao gerar relatório"
        raise HTTPException(status_code=500, detail=detail)

    return {"relatorio": resultado.stdout}