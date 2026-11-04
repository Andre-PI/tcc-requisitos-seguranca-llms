from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(title="Importador de Configuracao YAML")


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., min_length=1)


def _validar_raiz(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise HTTPException(
            status_code=422,
            detail="A raiz do documento YAML deve ser um mapeamento.",
        )

    for chave in obj.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=422,
                detail="Todas as chaves da raiz devem ser textuais.",
            )

    return obj


@app.post("/configuracao")
def importar_configuracao(entrada: ConfiguracaoEntrada) -> dict[str, Any]:
    try:
        documento = yaml.safe_load(entrada.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=f"YAML invalido: {exc}") from exc

    configuracao = _validar_raiz(documento)
    return {"configuracao": configuracao}