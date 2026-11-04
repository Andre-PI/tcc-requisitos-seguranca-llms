from typing import Any
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Importador de Configuração YAML")

MAX_YAML_LENGTH = 1_000_000


class ConfigInput(BaseModel):
    yaml: str = Field(..., max_length=MAX_YAML_LENGTH)


class SafeKeyDict(dict):
    """Subclasse de dict para interceptar inserções durante o carregamento de mapeamentos."""

    pass


class SafeYAMLValidatorLoader(yaml.SafeLoader):
    """Loader seguro que valida chaves textuais e estruturas permitidas."""

    pass


def construct_mapping_with_str_keys(loader: yaml.SafeLoader, node: yaml.MappingNode):
    loader.flatten_mapping(node)
    mapping = SafeKeyDict()
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=False)
        if not isinstance(key, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Todas as chaves de mapeamento devem ser textuais (strings).",
            )
        val = loader.construct_object(value_node, deep=False)
        mapping[key] = val
    return mapping


SafeYAMLValidatorLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping_with_str_keys
)


def normalize_structure(obj: Any) -> Any:
    """Converte instâncias de SafeKeyDict de volta para dicts convencionais e valida recursivamente."""
    if isinstance(obj, dict):
        normalized = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Todas as chaves de mapeamento devem ser textuais (strings).",
                )
            normalized[k] = normalize_structure(v)
        return normalized
    elif isinstance(obj, list):
        return [normalize_structure(item) for item in obj]
    return obj


@app.post("/configuracao", status_code=status.HTTP_200_OK)
def importar_configuracao(payload: ConfigInput):
    yaml_text = payload.yaml

    if not yaml_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O documento YAML não pode estar vazio.",
        )

    try:
        loaded_data = yaml.load(yaml_text, Loader=SafeYAMLValidatorLoader)
    except HTTPException:
        raise
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro de sintaxe no documento YAML: {exc}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Falha ao processar o documento YAML fornecido.",
        )

    if not isinstance(loaded_data, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz da configuração deve ser um mapeamento (objeto/dicionário).",
        )

    config_normalizada = normalize_structure(loaded_data)

    return {"configuracao": config_normalizada}