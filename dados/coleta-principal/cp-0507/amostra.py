from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., min_length=1)


def _validar_raiz(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("A raiz do YAML deve ser um mapeamento.")
    for chave in obj.keys():
        if not isinstance(chave, str):
            raise ValueError("Todas as chaves da raiz devem ser textuais.")
    return obj


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    try:
        configuracao = yaml.safe_load(payload.yaml)
        configuracao = _validar_raiz(configuracao)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML inválido: {exc}") from exc

    return {"configuracao": configuracao}