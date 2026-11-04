from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any
import yaml

app = FastAPI()

_configuracao: Any = None


class ImportarConfiguracaoRequest(BaseModel):
    yaml: str = Field(..., min_length=1)


@app.post("/configuracao")
def importar_configuracao(payload: ImportarConfiguracaoRequest):
    global _configuracao
    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML invalido: {e}") from e

    _configuracao = configuracao
    return {"configuracao": configuracao}