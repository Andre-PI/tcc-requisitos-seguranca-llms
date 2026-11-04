import math
from typing import Any
import yaml
from yaml.constructor import SafeConstructor
from yaml.nodes import MappingNode, ScalarNode, SequenceNode
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

MAX_BYTES = 16384
MAX_DEPTH = 20

ALLOWED_YAML_TAGS = {
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
    if not isinstance(node, MappingNode):
        raise yaml.constructor.ConstructorError(None, None, "Expected mapping", node.start_mark)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(None, None, "Keys must be strings", key_node.start_mark)
        if key in mapping:
            raise yaml.constructor.ConstructorError(None, None, f"Duplicate key: {key}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_no_duplicates,
)


def validate_node(node: Any, current_depth: int, visited_nodes: set):
    if id(node) in visited_nodes:
        raise ValueError("Cyclic reference detected")
    visited_nodes.add(id(node))

    try:
        if node.tag not in ALLOWED_YAML_TAGS:
            raise ValueError(f"Disallowed tag: {node.tag}")

        if isinstance(node, (MappingNode, SequenceNode)):
            if current_depth > MAX_DEPTH:
                raise ValueError("Maximum depth exceeded")

            if isinstance(node, MappingNode):
                for key_node, val_node in node.value:
                    if key_node.tag != "tag:yaml.org,2002:str":
                        raise ValueError("Map key must be string")
                    validate_node(key_node, current_depth, visited_nodes)
                    validate_node(val_node, current_depth + 1, visited_nodes)
            elif isinstance(node, SequenceNode):
                for item_node in node.value:
                    validate_node(item_node, current_depth + 1, visited_nodes)
    finally:
        visited_nodes.remove(id(node))


def validate_structure(obj: Any, current_depth: int, visited_objs: set):
    if id(obj) in visited_objs:
        raise ValueError("Cyclic reference detected")
    visited_objs.add(id(obj))

    try:
        if isinstance(obj, dict):
            if current_depth > MAX_DEPTH:
                raise ValueError("Maximum depth exceeded")
            for k, v in obj.items():
                if not isinstance(k, str):
                    raise ValueError("Dictionary keys must be strings")
                validate_structure(v, current_depth + 1, visited_objs)
        elif isinstance(obj, list):
            if current_depth > MAX_DEPTH:
                raise ValueError("Maximum depth exceeded")
            for item in obj:
                validate_structure(item, current_depth + 1, visited_objs)
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                raise ValueError("Non-finite numbers are not allowed")
        elif isinstance(obj, (int, str, bool)) or obj is None:
            pass
        else:
            raise ValueError("Unsupported data type")
    finally:
        visited_objs.remove(id(obj))


class YamlPayload(BaseModel):
    yaml: str


app = FastAPI()


@app.post("/configuracao")
def import_configuration(payload: YamlPayload):
    raw_yaml = payload.yaml
    yaml_bytes = raw_yaml.encode("utf-8")
    if len(yaml_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload exceeds maximum allowed size",
        )

    try:
        loader = StrictSafeLoader(raw_yaml)
        if not loader.check_node():
            raise ValueError("Empty YAML document")

        root_node = loader.get_node()
        if loader.check_node():
            raise ValueError("Multiple documents not supported")

        if not isinstance(root_node, MappingNode):
            raise ValueError("Root document must be a mapping")

        validate_node(root_node, current_depth=0, visited_nodes=set())

        parsed_data = loader.construct_document(root_node)
        if not isinstance(parsed_data, dict):
            raise ValueError("Root must be a mapping")

        validate_structure(parsed_data, current_depth=0, visited_objs=set())

    except (yaml.YAMLError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YAML configuration",
        )

    return {"configuracao": parsed_data}