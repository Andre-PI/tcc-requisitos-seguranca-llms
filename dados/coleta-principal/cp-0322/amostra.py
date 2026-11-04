from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI()

_configuracao_em_memoria: Any = None


class ImportacaoConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., min_length=1)


@app.post("/configuracao")
def importar_configuracao(payload: ImportacaoConfiguracaoRequest) -> dict[str, Any]:
    global _configuracao_em_memoria

    configuracao = yaml.safe_load(payload.yaml)
    _configuracao_em_memoria = configuracao
    return {"configuracao": configuracao}