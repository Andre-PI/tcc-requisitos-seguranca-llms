import math
from typing import Any
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, ScalarNode, SequenceNode
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

MAX_BYTES = 16384
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


def construct_mapping_no_duplicates(loader: StrictSafeLoader, node: MappingNode, deep: bool = False) -> dict:
    if not isinstance(node, MappingNode):
        raise ConstructorError(None, None, "Esperado mapeamento", node.start_mark)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ConstructorError(None, None, "A chave deve ser string", key_node.start_mark)
        if key in mapping:
            raise ConstructorError(None, None, "Chave duplicada encontrada", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_no_duplicates,
)


def validate_nodes_and_depth(node: Any, current_depth: int, visited_nodes: set) -> None:
    if node.tag not in ALLOWED_TAGS:
        raise ValueError("Tag YAML nao permitida")

    node_id = id(node)
    if node_id in visited_nodes:
        raise ValueError("Referencia ciclica detectada")
    visited_nodes.add(node_id)

    if isinstance(node, (MappingNode, SequenceNode)):
        if current_depth > MAX_DEPTH:
            raise ValueError("Profundidade maxima excedida")

        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                validate_nodes_and_depth(key_node, current_depth, visited_nodes)
                validate_nodes_and_depth(value_node, current_depth + 1, visited_nodes)
        elif isinstance(node, SequenceNode):
            for item_node in node.value:
                validate_nodes_and_depth(item_node, current_depth + 1, visited_nodes)

    visited_nodes.remove(node_id)


def validate_json_compatibility(data: Any) -> None:
    if isinstance(data, dict):
        for k, v in data.items():
            if not isinstance(k, str):
                raise ValueError("Chave de mapeamento invalida")
            validate_json_compatibility(v)
    elif isinstance(data, list):
        for item in data:
            validate_json_compatibility(item)
    elif isinstance(data, (str, bool)) or data is None:
        pass
    elif isinstance(data, (int, float)):
        if math.isnan(data) or math.isinf(data):
            raise ValueError("Numero nao finito nao suportado")
    else:
        raise ValueError("Tipo de dado incompativel com JSON")


app = FastAPI()


class ConfigRequest(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(payload: ConfigRequest):
    raw_yaml = payload.yaml
    if len(raw_yaml.encode("utf-8")) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Tamanho maximo do documento excedido.",
        )

    try:
        loader = StrictSafeLoader(raw_yaml)
        try:
            root_node = loader.get_single_node()
        finally:
            loader.dispose()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao processar o documento YAML.",
        )

    if root_node is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Documento YAML vazio ou invalido.",
        )

    if not isinstance(root_node, MappingNode):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A raiz da configuracao deve ser um mapeamento.",
        )

    try:
        validate_nodes_and_depth(root_node, current_depth=0, visited_nodes=set())
        parsed_loader = StrictSafeLoader(raw_yaml)
        try:
            config = parsed_loader.get_single_data()
        finally:
            parsed_loader.dispose()
        validate_json_compatibility(config)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuracao YAML invalida.",
        )

    if not isinstance(config, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A raiz da configuracao deve ser um mapeamento.",
        )

    return {"configuracao": config}