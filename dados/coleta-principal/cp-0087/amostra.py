from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest) -> Dict[str, Any]:
    try:
        dados = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML inválido: {exc}")

    if dados is None:
        dados = {}

    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=400,
            detail="A raiz da configuração deve ser um mapeamento (objeto).",
        )

    return {"configuracao": dados}