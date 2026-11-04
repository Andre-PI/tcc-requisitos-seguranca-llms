import os
import sys
import json
import re
import subprocess
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator

app = FastAPI()


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(min_length=1, max_length=5000)
    formato: Literal["json", "csv"]

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("categoria vazia")
        if "\x00" in v:
            raise ValueError("categoria invalida")
        return v


def _get_env_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise HTTPException(status_code=500, detail=f"Variavel de ambiente ausente: {name}")
    p = Path(value)
    if not p.is_absolute():
        raise HTTPException(status_code=500, detail=f"Caminho invalido em {name}")
    return p


def _validate_script_path(script: Path) -> None:
    try:
        resolved = script.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Utilitario nao encontrado")
    if not resolved.is_file():
        raise HTTPException(status_code=500, detail="Utilitario invalido")
    if resolved.suffix != ".py":
        pass


def _run_utilitario(categoria: str, formato: str) -> str:
    script = _get_env_path("TCC_RELATORIO_UTIL")
    _validate_script_path(script)

    cmd = [sys.executable, str(script), "--formato", formato, categoria]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
                "LANG": os.environ.get("LANG", "C.UTF-8"),
                "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
                "TCC_RELATORIO_DADOS": os.environ.get("TCC_RELATORIO_DADOS", ""),
                "TCC_RELATORIO_LOG": os.environ.get("TCC_RELATORIO_LOG", ""),
                "TCC_RELATORIO_UTIL": os.environ.get("TCC_RELATORIO_UTIL", ""),
            },
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tempo limite excedido ao executar utilitario")
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao executar utilitario")

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "Utilitario retornou erro"
        raise HTTPException(status_code=500, detail=detail[:2000])

    return proc.stdout


@app.post("/relatorio")
def relatorio(payload: RelatorioRequest):
    saida = _run_utilitario(payload.categoria, payload.formato)
    return {"relatorio": saida}