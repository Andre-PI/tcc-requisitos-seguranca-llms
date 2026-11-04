from typing import Any, Dict
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import yaml


app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    yaml: str


class ConfiguracaoResponse(BaseModel):
    configuracao: Dict[str, Any]


@app.post(
    "/configuracao",
    response_model=ConfiguracaoResponse,
    status_code=status.HTTP_200_OK,
)
def importar_configuracao(payload: ConfiguracaoRequest):
    try:
        dados = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"YAML inválido: {str(exc)}",
        )

    if dados is None:
        dados = {}

    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz da configuração deve ser um mapeamento.",
        )

    for chave in dados.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Todas as chaves da raiz devem ser textuais.",
            )

    return {"configuracao": dados}