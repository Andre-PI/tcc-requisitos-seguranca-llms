from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()

class ConfigInput(BaseModel):
    yaml: str

estado_configuracao: Any = None

@app.post("/configuracao")
async def importar_configuracao(dados: ConfigInput):
    global estado_configuracao
    try:
        objeto = yaml.safe_load(dados.yaml)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao analisar YAML: {e}")
    estado_configuracao = objeto
    return {"configuracao": objeto}