from typing import Any
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()

MAX_YAML_LENGTH = 1_000_000


class ConfigImportRequest(BaseModel):
    yaml: str = Field(..., max_length=MAX_YAML_LENGTH)


class SafeKeyValidationLoader(yaml.SafeLoader):
    pass


def construct_mapping_with_str_keys(
    loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[str, Any]:
    mapping = loader.construct_mapping(node, deep=deep)
    for key in mapping:
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                None,
                None,
                f"Todas as chaves de mapeamento devem ser texto. Chave invalida encontrada: {key!r}",
                node.start_mark,
            )
    return mapping


SafeKeyValidationLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_with_str_keys,
)


@app.post("/configuracao", status_code=status.HTTP_200_OK)
def importar_configuracao(payload: ConfigImportRequest) -> dict[str, Any]:
    yaml_content = payload.yaml

    try:
        data = yaml.load(yaml_content, Loader=SafeKeyValidationLoader)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro ao processar documento YAML: {exc}",
        )

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz da configuracao deve ser um mapeamento (dicionario).",
        )

    return {"configuracao": data}