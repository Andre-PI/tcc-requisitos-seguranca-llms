from typing import Any, Dict
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import yaml


app = FastAPI()

MAX_YAML_LENGTH = 1_000_000


class ConfiguracaoRequest(BaseModel):
    yaml: str = Field(..., max_length=MAX_YAML_LENGTH)


class ConfiguracaoResponse(BaseModel):
    configuracao: Dict[str, Any]


def validar_chaves_str(dado: Any) -> None:
    if isinstance(dado, dict):
        for k, v in dado.items():
            if not isinstance(k, str):
                raise ValueError("Todas as chaves dos mapeamentos devem ser texto.")
            validar_chaves_str(v)
    elif isinstance(dado, list):
        for item in dado:
            validar_chaves_str(item)


@app.post(
    "/configuracao",
    response_model=ConfiguracaoResponse,
    status_code=status.HTTP_200_OK,
)
def importar_configuracao(payload: ConfiguracaoRequest):
    yaml_text = payload.yaml

    if not yaml_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O documento YAML não pode estar vazio.",
        )

    try:
        dados = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro de sintaxe no YAML: {exc}",
        )

    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz do documento YAML deve ser um mapeamento.",
        )

    try:
        validar_chaves_str(dados)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return {"configuracao": dados}