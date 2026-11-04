from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., min_length=1)


app = FastAPI()


@app.post("/configuracao")
async def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail="YAML inválido") from exc

    if configuracao is None:
        raise HTTPException(status_code=400, detail="A configuração YAML não pode ser nula")

    if not isinstance(configuracao, dict):
        raise HTTPException(
            status_code=400,
            detail="A raiz da configuração deve ser um mapeamento com chaves textuais",
        )

    for chave in configuracao.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=400,
                detail="A raiz da configuração deve conter apenas chaves textuais",
            )

    return {"configuracao": configuracao}