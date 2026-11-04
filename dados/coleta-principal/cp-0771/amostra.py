from typing import Any
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="YAML Configuration Importer")


class ConfigPayload(BaseModel):
    yaml: str = Field(..., max_length=1_000_000)


def validate_mapping_keys(data: Any) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(key, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Todas as chaves dos mapeamentos devem ser strings.",
                )
            validate_mapping_keys(value)
    elif isinstance(data, list):
        for item in data:
            validate_mapping_keys(item)


@app.post("/configuracao", status_code=status.HTTP_200_OK)
def importar_configuracao(payload: ConfigPayload) -> dict[str, Any]:
    try:
        conteudo = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"YAML inválido: {exc}",
        )

    if not isinstance(conteudo, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz da configuração deve ser um mapeamento (objeto).",
        )

    validate_mapping_keys(conteudo)

    return {"configuracao": conteudo}