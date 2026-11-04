import os
import sys
import json
import csv
import shlex
import subprocess
from pathlib import Path
from typing import Literal, Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict, field_validator


app = FastAPI()


class RelatorioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(..., min_length=1, max_length=500)
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


def _obter_ambiente() -> tuple[Path, Path | None, Path | None]:
    util = os.environ.get("TCC_RELATORIO_UTIL")
    if not util:
        raise RuntimeError("TCC_RELATORIO_UTIL nao definido")
    util_path = Path(util)
    if not util_path.is_file():
        raise RuntimeError("utilitario invalido")

    dados_env = os.environ.get("TCC_RELATORIO_DADOS")
    log_env = os.environ.get("TCC_RELATORIO_LOG")
    dados_path = Path(dados_env) if dados_env else None
    log_path = Path(log_env) if log_env else None
    return util_path, dados_path, log_path


def _executar_utilitario(categoria: str, formato: str) -> str:
    util_path, dados_path, log_path = _obter_ambiente()

    cmd = [sys.executable, str(util_path), "--formato", formato, categoria]
    env = os.environ.copy()

    if dados_path is not None:
        env["TCC_RELATORIO_DADOS"] = str(dados_path)
    if log_path is not None:
        env["TCC_RELATORIO_LOG"] = str(log_path)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            env=env,
            check=False,
        )
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="falha ao executar utilitario",
        )

    if proc.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="utilitario retornou erro",
        )

    return proc.stdout


@app.post("/relatorio")
def relatorio(req: RelatorioRequest) -> dict[str, Any]:
    saida = _executar_utilitario(req.categoria, req.formato)
    return {"relatorio": saida}