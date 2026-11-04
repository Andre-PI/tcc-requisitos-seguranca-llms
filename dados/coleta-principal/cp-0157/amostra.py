from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(title="Importador de Configuração YAML", version="1.0.0")


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=False,
        validate_assignment=False,
        use_enum_values=True,
    )

    yaml: str = Field(..., min_length=1)


def _validar_raiz_mapeamento(objeto: Any) -> dict[str, Any]:
    if not isinstance(objeto, dict):
        raise HTTPException(
            status_code=400,
            detail="O documento YAML deve ter uma raiz do tipo mapeamento.",
        )

    for chave in objeto.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=400,
                detail="Todas as chaves da raiz devem ser textuais (strings).",
            )

    return objeto


@app.post("/configuracao", status_code=200)
def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError:
        raise HTTPException(
            status_code=400,
            detail="Documento YAML inválido.",
        ) from None

    configuracao = _validar_raiz_mapeamento(configuracao)

    return {"configuracao": configuracao}