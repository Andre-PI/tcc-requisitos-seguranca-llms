from typing import Any, Dict
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import yaml


app = FastAPI(title="YAML Configuration Importer")


class ConfigPayload(BaseModel):
    yaml: str = Field(..., max_length=1_000_000)


def validate_mapping_keys(data: Any) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(key, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Todas as chaves de mapeamentos devem ser strings.",
                )
            validate_mapping_keys(value)
    elif isinstance(data, list):
        for item in data:
            validate_mapping_keys(item)


@app.post("/configuracao", status_code=status.HTTP_200_OK)
def importar_configuracao(payload: ConfigPayload) -> Dict[str, Any]:
    yaml_text = payload.yaml

    if not yaml_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O documento YAML não pode estar vazio.",
        )

    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro de sintaxe no documento YAML: {exc}",
        )

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz do documento YAML deve ser um mapeamento.",
        )

    validate_mapping_keys(data)

    return {"configuracao": data}