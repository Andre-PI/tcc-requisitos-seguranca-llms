from typing import Any
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()

MAX_YAML_LENGTH = 1_000_000


class ConfigRequest(BaseModel):
    yaml: str = Field(..., max_length=MAX_YAML_LENGTH)


class SafeLoaderWithKeyValidation(yaml.SafeLoader):
    pass


def _validate_keys(node: yaml.Node) -> None:
    if isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            if not isinstance(key_node, yaml.ScalarNode) or key_node.tag not in (
                "tag:yaml.org,2002:str",
                "tag:yaml.org,2002:null",
            ):
                raise ValueError("As chaves de mapeamento devem ser strings.")
            _validate_keys(value_node)
    elif isinstance(node, yaml.SequenceNode):
        for item_node in node.value:
            _validate_keys(item_node)


def parse_yaml_safely(yaml_text: str) -> dict[str, Any]:
    try:
        loader = SafeLoaderWithKeyValidation(yaml_text)
        try:
            node = loader.get_single_node()
        finally:
            loader.dispose()

        if node is None:
            raise ValueError("O documento YAML está vazio.")

        if not isinstance(node, yaml.MappingNode):
            raise ValueError("A raiz da configuração deve ser um mapeamento.")

        _validate_keys(node)

        data = yaml.safe_load(yaml_text)

        if not isinstance(data, dict):
            raise ValueError("A raiz da configuração deve ser um mapeamento.")

        for key in data.keys():
            if not isinstance(key, str):
                raise ValueError("Todas as chaves da raiz devem ser strings textuais.")

        return data
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro de sintaxe no YAML: {str(exc)}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@app.post("/configuracao", status_code=status.HTTP_200_OK)
def importar_configuracao(payload: ConfigRequest) -> dict[str, Any]:
    configuracao = parse_yaml_safely(payload.yaml)
    return {"configuracao": configuracao}