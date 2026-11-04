from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(title="Importador de Configuracao YAML")

_configuracao_atual: Any = None


class ImportacaoYAMLRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    yaml: str = Field(..., min_length=1)


@app.post("/configuracao")
def importar_configuracao(payload: ImportacaoYAMLRequest) -> dict[str, Any]:
    global _configuracao_atual

    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML invalido: {exc}") from exc

    _configuracao_atual = configuracao
    return {"configuracao": configuracao}