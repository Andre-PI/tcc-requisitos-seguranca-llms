from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any
import yaml

app = FastAPI()

class ConfigRequest(BaseModel):
    yaml: str

@app.post("/configuracao")
async def importar_configuracao(req: ConfigRequest):
    try:
        obj = yaml.safe_load(req.yaml)
        if not isinstance(obj, dict):
            raise HTTPException(status_code=400, detail="Configuração raiz deve ser um mapeamento (dict).")
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao parsear YAML: {e}")
    return {"configuracao": obj}