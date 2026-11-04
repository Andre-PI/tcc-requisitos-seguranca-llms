from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()

_estado_configuracao: Any = None


class ConfigYAMLRequest(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(dados: ConfigYAMLRequest):
    global _estado_configuracao
    try:
        objeto_importado = yaml.safe_load(dados.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML inválido: {exc}")
    
    _estado_configuracao = objeto_importado
    return {"configuracao": objeto_importado}