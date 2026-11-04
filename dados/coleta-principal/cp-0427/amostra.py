import math
from typing import Any
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, ScalarNode, SequenceNode
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()

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


class SafeStrictLoader(yaml.SafeLoader):
    pass


def construct_mapping_strict(loader: SafeStrictLoader, node: MappingNode, deep: bool = False) -> dict:
    if not isinstance(node, MappingNode):
        raise ConstructorError(None, None, "Expected mapping node", node.start_mark)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ConstructorError(None, None, "Mapping keys must be strings", key_node.start_mark)
        if key in mapping:
            raise ConstructorError(None, None, f"Duplicate key: {key}", key_node.start_mark)
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


SafeStrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_strict,
)


class ConfigRequest(BaseModel):
    yaml: str = Field(..., description="YAML document content as text")


def validate_node(node: Any, depth: int, visited_nodes: set) -> None:
    if id(node) in visited_nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cyclic reference detected",
        )

    if node.tag not in ALLOWED_TAGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disallowed or custom YAML tag detected",
        )

    if isinstance(node, (MappingNode, SequenceNode)):
        if depth > MAX_DEPTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum container depth exceeded",
            )
        visited_nodes.add(id(node))
        if isinstance(node, MappingNode):
            for k_node, v_node in node.value:
                validate_node(k_node, depth, visited_nodes)
                validate_node(v_node, depth + 1, visited_nodes)
        elif isinstance(node, SequenceNode):
            for item_node in node.value:
                validate_node(item_node, depth + 1, visited_nodes)
        visited_nodes.remove(id(node))


def validate_values(val: Any, visited_objects: set) -> None:
    if id(val) in visited_objects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cyclic structure detected in parsed values",
        )

    if val is None or isinstance(val, (bool, str)):
        return
    elif isinstance(val, int):
        return
    elif isinstance(val, float):
        if not math.isfinite(val):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Non-finite numbers are not allowed",
            )
        return
    elif isinstance(val, list):
        visited_objects.add(id(val))
        for item in val:
            validate_values(item, visited_objects)
        visited_objects.remove(id(val))
    elif isinstance(val, dict):
        visited_objects.add(id(val))
        for k, v in val.items():
            if not isinstance(k, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mapping keys must be strings",
                )
            validate_values(v, visited_objects)
        visited_objects.remove(id(val))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported data type detected",
        )


@app.post("/configuracao", status_code=status.HTTP_200_OK)
def importar_configuracao(req: ConfigRequest):
    content_bytes = req.yaml.encode("utf-8")
    if len(content_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="YAML document exceeds maximum allowed size",
        )

    if not req.yaml.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YAML document is empty",
        )

    try:
        loader = SafeStrictLoader(req.yaml)
        root_node = loader.get_single_node()
    except yaml.YAMLError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YAML syntax or multiple documents detected",
        )

    if root_node is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YAML document is empty",
        )

    if not isinstance(root_node, MappingNode):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Root of configuration must be a mapping",
        )

    validate_node(root_node, depth=0, visited_nodes=set())

    try:
        loader = SafeStrictLoader(req.yaml)
        data = loader.get_single_data()
    except yaml.YAMLError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse YAML content",
        )

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Root of configuration must be a mapping",
        )

    validate_values(data, set())

    return {"configuracao": data}