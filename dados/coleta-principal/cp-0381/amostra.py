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


class UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def construct_mapping(loader, node, deep=False):
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            None, None, f"expected a mapping node, but found {node.id}", node.start_mark
        )
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found non-string key",
                key_node.start_mark,
            )
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key: {key}",
                key_node.start_mark,
            )
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
)


def validate_nodes(node, depth=0, seen=None):
    if seen is None:
        seen = set()

    node_id = id(node)
    if node_id in seen:
        raise ValueError("Cyclic reference detected.")
    seen.add(node_id)

    tag = getattr(node, "tag", None)
    if tag not in ALLOWED_TAGS:
        raise ValueError("Disallowed tag detected.")

    if isinstance(node, (yaml.MappingNode, yaml.SequenceNode)):
        if depth > MAX_DEPTH:
            raise ValueError("Exceeded maximum container depth.")

    if isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            validate_nodes(key_node, depth, seen.copy())
            validate_nodes(value_node, depth + 1, seen.copy())
    elif isinstance(node, yaml.SequenceNode):
        for child in node.value:
            validate_nodes(child, depth + 1, seen.copy())


def validate_json_compat(value, depth=0, seen=None):
    if seen is None:
        seen = set()

    obj_id = id(value)

    if isinstance(value, dict):
        if obj_id in seen:
            raise ValueError("Cyclic reference detected.")
        seen.add(obj_id)
        if depth > MAX_DEPTH:
            raise ValueError("Exceeded maximum container depth.")
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError("Mapping keys must be strings.")
            validate_json_compat(v, depth + 1, seen.copy())
    elif isinstance(value, list):
        if obj_id in seen:
            raise ValueError("Cyclic reference detected.")
        seen.add(obj_id)
        if depth > MAX_DEPTH:
            raise ValueError("Exceeded maximum container depth.")
        for item in value:
            validate_json_compat(item, depth + 1, seen.copy())
    elif isinstance(value, (str, bool, type(None))):
        return
    elif isinstance(value, int):
        return
    elif isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("Non-finite numbers are not allowed.")
    else:
        raise ValueError("Incompatible JSON data type.")


class YamlPayload(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(payload: YamlPayload):
    encoded_bytes = payload.yaml.encode("utf-8")
    if len(encoded_bytes) > MAX_YAML_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload exceeds maximum permitted size.",
        )

    try:
        loader = UniqueKeySafeLoader(payload.yaml)
        try:
            if not loader.check_node():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid YAML configuration.",
                )
            root_node = loader.get_node()
            if loader.check_node():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Multiple documents are not supported.",
                )
        finally:
            loader.dispose()

        if not isinstance(root_node, yaml.MappingNode):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Root must be a mapping.",
            )

        validate_nodes(root_node, depth=0)

        loader = UniqueKeySafeLoader(payload.yaml)
        try:
            parsed_data = loader.get_single_data()
        finally:
            loader.dispose()

        if not isinstance(parsed_data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Root must be a mapping.",
            )

        validate_json_compat(parsed_data, depth=0)

        return {"configuracao": parsed_data}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YAML configuration.",
        )