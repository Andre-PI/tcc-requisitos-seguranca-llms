from typing import Any
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()

MAX_YAML_LENGTH = 1_000_000


class ConfigRequest(BaseModel):
    yaml: str = Field(..., max_length=MAX_YAML_LENGTH)


class SafeLoaderWithAliases(yaml.SafeLoader):
    pass


def validate_mapping(data: Any) -> None:
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz da configuracao deve ser um mapeamento.",
        )

    stack = [data]
    visited = set()

    while stack:
        current = stack.pop()
        current_id = id(current)
        if current_id in visited:
            continue
        visited.add(current_id)

        if isinstance(current, dict):
            for k, v in current.items():
                if not isinstance(k, str):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Todas as chaves de mapeamento devem ser textuais.",
                    )
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)):
                    stack.append(item)


@app.post("/configuracao", status_code=status.HTTP_200_OK)
def importar_configuracao(payload: ConfigRequest):
    yaml_text = payload.yaml

    try:
        data = yaml.load(yaml_text, Loader=SafeLoaderWithAliases)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro ao processar documento YAML: {str(exc)}",
        )

    validate_mapping(data)

    return {"configuracao": data}