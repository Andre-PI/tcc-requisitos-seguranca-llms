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
            status_code=422, detail=f"Erro ao processar YAML: {str(exc)}"
        )

    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=422,
            detail="A raiz da configuracao deve ser um mapeamento (objeto).",
        )

    for chave in dados.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=422,
                detail="Todas as chaves da raiz devem ser textuais (strings).",
            )

    return {"configuracao": dados}