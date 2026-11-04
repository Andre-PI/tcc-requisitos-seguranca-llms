from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict


app = FastAPI()

_configuracao_em_memoria: Any = None


class ConfiguracaoImportacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str


@app.post("/configuracao")
async def importar_configuracao(payload: ConfiguracaoImportacao) -> dict[str, Any]:
    global _configuracao_em_memoria

    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail="YAML invalido") from exc

    _configuracao_em_memoria = configuracao
    return {"configuracao": configuracao}