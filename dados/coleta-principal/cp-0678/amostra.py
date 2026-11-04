from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    yaml: str


class ConfiguracaoResponse(BaseModel):
    configuracao: Dict[str, Any]


@app.post("/configuracao", response_model=ConfiguracaoResponse, status_code=200)
def importar_configuracao(payload: ConfiguracaoRequest):
    try:
        dados = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=422, detail=f"Erro ao analisar o YAML: {str(exc)}"
        )

    if dados is None:
        dados = {}

    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=422,
            detail="A raiz da configuração YAML deve ser um mapeamento (dicionário).",
        )

    return {"configuracao": dados}