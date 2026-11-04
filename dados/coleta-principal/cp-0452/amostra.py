from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()

_config_state: Any = None


class ConfigPayload(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(payload: ConfigPayload) -> dict[str, Any]:
    global _config_state
    try:
        conteudo = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=400, detail=f"Erro ao processar YAML: {exc}"
        ) from exc

    _config_state = conteudo
    return {"configuracao": _config_state}