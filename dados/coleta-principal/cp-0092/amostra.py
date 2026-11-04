import math
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()

MAX_YAML_BYTES = 16384
MAX_DEPTH = 20

ALLOWED_TAGS = {
    "tag:yaml.org,2002:null",
    "tag:yaml.org,2002:bool",
    "tag:yaml.org,2002:int",
    "tag:yaml.org,2002:float",
    "tag:yaml.org,2002:str",
    "tag:yaml.org,2002:seq",
    "tag:yaml.org,2002:map",
}


class StrictSafeLoader(yaml.SafeLoader):
    pass


def construct_mapping_no_duplicates(loader, node, deep=False):
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            None, None, "Esperado mapeamento", node.start_mark
        )
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "chave duplicada detectada", None, None, key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_no_duplicates,
)


class ConfigRequest(BaseModel):
    yaml: str


def check_node_safety(node, seen_nodes):
    if node in seen_nodes:
        raise ValueError("Referencia ciclica detectada")
    seen_nodes.add(node)

    if node.tag not in ALLOWED_TAGS:
        raise ValueError("Tag YAML nao permitida")

    if isinstance(node, yaml.SequenceNode):
        for item in node.value:
            check_node_safety(item, seen_nodes)
    elif isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            check_node_safety(key_node, seen_nodes)
            check_node_safety(value_node, seen_nodes)

    seen_nodes.remove(node)


def validate_and_sanitize(obj, depth=0):
    if depth > MAX_DEPTH:
        raise ValueError("Profundidade maxima excedida")

    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError("Chave de mapeamento deve ser texto")
            result[k] = validate_and_sanitize(v, depth + 1)
        return result
    elif isinstance(obj, list):
        return [validate_and_sanitize(item, depth + 1) for item in obj]
    elif isinstance(obj, bool):
        return obj
    elif isinstance(obj, int):
        return obj
    elif isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("Valor float nao finito")
        return obj
    elif isinstance(obj, str):
        return obj
    elif obj is None:
        return None
    else:
        raise ValueError("Tipo incompativel com JSON")


@app.post("/configuracao")
def importar_configuracao(payload: ConfigRequest):
    raw_yaml = payload.yaml
    if len(raw_yaml.encode("utf-8")) > MAX_YAML_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Tamanho maximo do documento excedido",
        )

    loader = StrictSafeLoader(raw_yaml)
    try:
        if not loader.check_node():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Documento YAML vazio ou invalido",
            )

        root_node = loader.get_node()

        if loader.check_node():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiplos documentos YAML nao permitidos",
            )

        if not isinstance(root_node, yaml.MappingNode):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A raiz da configuracao deve ser um mapeamento",
            )

        check_node_safety(root_node, set())
        parsed = loader.construct_document(root_node)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Documento YAML invalido",
        )
    finally:
        loader.dispose()

    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A raiz da configuracao deve ser um mapeamento",
        )

    try:
        sanitized = validate_and_sanitize(parsed, depth=0)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuracao invalida ou tipos incompativeis",
        )

    return {"configuracao": sanitized}