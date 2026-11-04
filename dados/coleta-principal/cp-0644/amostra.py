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


def validar_chaves(dado: Any) -> None:
    if isinstance(dado, dict):
        for chave, valor in dado.items():
            if not isinstance(chave, str):
                raise ValueError("Todas as chaves dos mapeamentos devem ser strings.")
            validar_chaves(valor)
    elif isinstance(dado, list):
        for item in dado:
            validar_chaves(item)


@app.post(
    "/configuracao",
    response_model=ConfiguracaoResponse,
    status_code=status.HTTP_200_OK,
)
def importar_configuracao(payload: ConfiguracaoRequest) -> ConfiguracaoResponse:
    try:
        conteudo = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Sintaxe YAML inválida: {str(exc)}",
        )

    if not isinstance(conteudo, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz da configuração deve ser um mapeamento (objeto).",
        )

    try:
        validar_chaves(conteudo)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return ConfiguracaoResponse(configuracao=conteudo)