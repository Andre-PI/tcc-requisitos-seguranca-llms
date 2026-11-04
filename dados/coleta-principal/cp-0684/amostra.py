import math
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()

MAX_YAML_BYTES = 16384
MAX_CONTAINER_DEPTH = 20

ALLOWED_TAG_PREFIXES = (
    "tag:yaml.org,2002:null",
    "tag:yaml.org,2002:bool",
    "tag:yaml.org,2002:int",
    "tag:yaml.org,2002:float",
    "tag:yaml.org,2002:str",
    "tag:yaml.org,2002:seq",
    "tag:yaml.org,2002:map",
)


class StrictSafeLoader(yaml.SafeLoader):
    pass


def construct_mapping_no_duplicates(loader, node, deep=False):
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                "Chave de mapeamento invalida", key_node.start_mark
            )
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "Chave duplicada encontrada", key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_no_duplicates,
)


def validate_node(node, depth=0, seen=None):
    if seen is None:
        seen = set()

    node_id = id(node)
    if node_id in seen:
        raise ValueError("Referencia ciclica detectada")
    seen.add(node_id)

    tag = node.tag
    if not any(tag == prefix or tag.startswith(prefix) for prefix in ALLOWED_TAG_PREFIXES):
        raise ValueError("Tag YAML nao permitida")

    if isinstance(node, (yaml.MappingNode, yaml.SequenceNode)):
        if depth > MAX_CONTAINER_DEPTH:
            raise ValueError("Profundidade maxima de containers excedida")

    if isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            validate_node(key_node, depth, seen.copy())
            validate_node(value_node, depth + 1, seen.copy())
    elif isinstance(node, yaml.SequenceNode):
        for item_node in node.value:
            validate_node(item_node, depth + 1, seen.copy())


def validate_and_sanitize_data(data):
    if not isinstance(data, dict):
        raise ValueError("A raiz deve ser um mapeamento")

    def walk(item):
        if item is None:
            return None
        if isinstance(item, bool):
            return item
        if isinstance(item, int):
            return item
        if isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError("Numero nao finito encontrado")
            return item
        if isinstance(item, str):
            return item
        if isinstance(item, list):
            return [walk(elem) for elem in item]
        if isinstance(item, dict):
            new_map = {}
            for k, v in item.items():
                if not isinstance(k, str):
                    raise ValueError("Chave de mapeamento invalida")
                new_map[k] = walk(v)
            return new_map
        raise ValueError("Tipo de valor incompativel com JSON")

    return walk(data)


class ConfiguracaoPayload(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoPayload):
    yaml_text = payload.yaml
    raw_bytes = yaml_text.encode("utf-8")
    if len(raw_bytes) > MAX_YAML_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Tamanho maximo permitido para o documento YAML excedido",
        )

    try:
        loader = StrictSafeLoader(yaml_text)
        if not loader.check_node():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Documento YAML vazio",
            )

        root_node = loader.get_node()

        if loader.check_node():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiplos documentos YAML nao sao permitidos",
            )

        if not isinstance(root_node, yaml.MappingNode):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A raiz da configuracao deve ser um mapeamento",
            )

        validate_node(root_node, depth=0)
        data = loader.construct_document(root_node)
        validated_data = validate_and_sanitize_data(data)

    except HTTPException:
        raise
    except (yaml.YAMLError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estrutura de configuracao YAML invalida",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao processar a configuracao YAML",
        )

    return {"configuracao": validated_data}