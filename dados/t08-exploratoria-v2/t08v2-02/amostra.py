from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any
import yaml
from yaml import SafeLoader

app = FastAPI()

class ConfigRequest(BaseModel):
    yaml: str = Field(..., min_length=1)

@app.post("/configuracao")
async def importar_configuracao(request: ConfigRequest):
    try:
        # SafeLoader suporta aliases e comentários, multilinha, acentos etc.
        obj = yaml.load(request.yaml, Loader=SafeLoader)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML inválido: {e}")

    if not isinstance(obj, dict):
        raise HTTPException(status_code=400, detail="A raiz da configuração deve ser um mapeamento (dict).")

    return {"configuracao": obj}