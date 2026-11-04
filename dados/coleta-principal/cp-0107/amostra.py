from typing import Any
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()

MAX_YAML_LENGTH = 1_000_000


class ConfigImportRequest(BaseModel):
    yaml: str = Field(..., max_length=MAX_YAML_LENGTH)


class ConfigImportResponse(BaseModel):
    configuracao: dict[str, Any]


def validate_mapping_keys(data: Any) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(key, str):
                raise ValueError("Todas as chaves de mapeamento devem ser strings.")
            validate_mapping_keys(value)
    elif isinstance(data, list):
        for item in data:
            validate_mapping_keys(item)


@app.post(
    "/configuracao",
    response_model=ConfigImportResponse,
    status_code=status.HTTP_200_OK,
)
def importar_configuracao(payload: ConfigImportRequest) -> ConfigImportResponse:
    raw_yaml = payload.yaml

    if not raw_yaml.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O documento YAML não pode estar vazio.",
        )

    try:
        parsed_data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro de sintaxe no documento YAML: {exc}",
        ) from exc

    if not isinstance(parsed_data, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz do documento YAML deve ser um mapeamento.",
        )

    try:
        validate_mapping_keys(parsed_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ConfigImportResponse(configuracao=parsed_data)