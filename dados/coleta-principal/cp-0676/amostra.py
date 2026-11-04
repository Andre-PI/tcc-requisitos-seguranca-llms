from typing import Any
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()

MAX_YAML_LENGTH = 1_000_000


class ConfiguracaoRequest(BaseModel):
    yaml: str = Field(..., max_length=MAX_YAML_LENGTH)


class ConfiguracaoResponse(BaseModel):
    configuracao: dict[str, Any]


def validar_chaves(data: Any) -> None:
    if isinstance(data, dict):
        for k, v in data.items():
            if not isinstance(k, str):
                raise ValueError("Todas as chaves dos mapeamentos devem ser strings.")
            validar_chaves(v)
    elif isinstance(data, list):
        for item in data:
            validar_chaves(item)


@app.post("/configuracao", response_model=ConfiguracaoResponse, status_code=status.HTTP_200_OK)
def importar_configuracao(payload: ConfiguracaoRequest) -> ConfiguracaoResponse:
    yaml_content = payload.yaml.strip()
    if not yaml_content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O documento YAML não pode ser vazio.",
        )

    try:
        dados = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro ao processar sintaxe YAML: {str(exc)}",
        )

    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz do documento YAML deve ser um mapeamento.",
        )

    try:
        validar_chaves(dados)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return ConfiguracaoResponse(configuracao=dados)