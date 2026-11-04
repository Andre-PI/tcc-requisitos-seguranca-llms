from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(title="Importador de Configuração YAML", version="1.0.0")


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    yaml: str = Field(..., min_length=1)


def _validar_configuracao(objeto: Any) -> dict[str, Any]:
    if not isinstance(objeto, dict):
        raise HTTPException(
            status_code=400,
            detail="A raiz do YAML deve ser um mapeamento com chaves textuais.",
        )

    for chave in objeto.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=400,
                detail="A raiz do YAML deve conter apenas chaves textuais.",
            )

    return objeto


@app.post("/configuracao", status_code=200)
async def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError:
        raise HTTPException(
            status_code=400,
            detail="Documento YAML inválido.",
        ) from None

    configuracao = _validar_configuracao(configuracao)
    return {"configuracao": configuracao}