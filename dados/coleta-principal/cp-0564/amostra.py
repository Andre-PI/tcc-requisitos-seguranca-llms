from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(title="Importador de Configuracao YAML")

_configuracao_em_memoria: Any = None


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., description="Conteudo YAML a ser importado")


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    global _configuracao_em_memoria

    configuracao = yaml.safe_load(payload.yaml)
    _configuracao_em_memoria = configuracao
    return {"configuracao": configuracao}