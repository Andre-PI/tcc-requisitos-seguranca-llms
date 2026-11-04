from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()

_config_store: Any = None


class ConfigPayload(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(payload: ConfigPayload):
    global _config_store
    try:
        dados = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML inválido: {str(exc)}")

    _config_store = dados
    return {"configuracao": dados}