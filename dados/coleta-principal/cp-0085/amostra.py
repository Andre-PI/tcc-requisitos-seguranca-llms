import math
from typing import Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

app = FastAPI()


class ConfigRequest(BaseModel):
    yaml: str


class SafeUniqueLoader(yaml.SafeLoader):
    pass


def construct_mapping_no_duplicates(loader: yaml.Loader, node: MappingNode) -> dict:
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=False)
        try:
            hash(key)
        except TypeError:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found unhashable key",
                key_node.start_mark,
            )
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found duplicate key",
                key_node.start_mark,
            )
        value = loader.construct_object(value_node, deep=False)
        mapping[key] = value
    return mapping


SafeUniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_no_duplicates,
)


def validate_structure(obj: Any, depth: int = 0) -> None:
    if depth > 20:
        raise ValueError("Container depth exceeds allowed limit.")

    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError("Mapping keys must be strings.")
            validate_structure(v, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            validate_structure(item, depth + 1)
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("Numeric values must be finite.")
    elif isinstance(obj, str):
        pass
    elif obj is None:
        pass
    else:
        raise ValueError("Value is not JSON compatible.")


@app.post("/configuracao", status_code=status.HTTP_200_OK)
def import_configuration(payload: ConfigRequest):
    raw_yaml = payload.yaml
    if len(raw_yaml.encode("utf-8")) > 16384:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload size exceeds maximum allowed limit.",
        )

    try:
        loader = SafeUniqueLoader(raw_yaml)
        try:
            if not loader.check_node():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid YAML document.",
                )

            root_node = loader.get_node()

            if loader.check_node():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid YAML document.",
                )

            allowed_tags = {
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG,
                yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG,
                "tag:yaml.org,2002:str",
                "tag:yaml.org,2002:int",
                "tag:yaml.org,2002:float",
                "tag:yaml.org,2002:bool",
                "tag:yaml.org,2002:null",
            }

            def check_nodes_and_depth(
                node: Any, current_depth: int, visited: set
            ) -> None:
                if id(node) in visited:
                    raise ValueError("Cyclic reference detected.")
                if node.tag not in allowed_tags:
                    raise ValueError("Disallowed or custom tag detected.")

                if isinstance(node, (MappingNode, SequenceNode)):
                    if current_depth > 20:
                        raise ValueError("Container depth exceeds allowed limit.")
                    visited.add(id(node))
                    if isinstance(node, MappingNode):
                        for k, v in node.value:
                            check_nodes_and_depth(k, current_depth, visited)
                            check_nodes_and_depth(v, current_depth + 1, visited)
                    elif isinstance(node, SequenceNode):
                        for item in node.value:
                            check_nodes_and_depth(item, current_depth + 1, visited)
                    visited.remove(id(node))

            check_nodes_and_depth(root_node, 0, set())

            data = loader.construct_document(root_node)
        finally:
            loader.dispose()

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Root configuration must be a mapping.",
            )

        validate_structure(data, 0)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse and validate YAML configuration.",
        )

    return {"configuracao": data}