import math
from typing import Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import yaml
from yaml.constructor import ConstructorError


class SafeLoaderNoDuplicates(yaml.SafeLoader):
    pass


ALLOWED_PREFIXES = ("tag:yaml.org,2002:",)


def check_tag(loader: SafeLoaderNoDuplicates, node: yaml.Node) -> None:
    tag = getattr(node, "tag", "")
    if not tag or not any(tag.startswith(p) or tag == p for p in ALLOWED_PREFIXES):
        raise yaml.YAMLError("Custom and python tags are rejected")
    if tag.startswith("tag:yaml.org,2002:python/"):
        raise yaml.YAMLError("Python tags are rejected")


def construct_mapping_no_duplicates(
    loader: SafeLoaderNoDuplicates, node: yaml.MappingNode, deep: bool = False
) -> dict:
    check_tag(loader, node)
    mapping = {}
    for key_node, value_node in node.value:
        check_tag(loader, key_node)
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.YAMLError("Keys must be strings")
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key: {key}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


def construct_sequence_checked(
    loader: SafeLoaderNoDuplicates, node: yaml.SequenceNode, deep: bool = False
) -> list:
    check_tag(loader, node)
    return [loader.construct_object(child, deep=deep) for child in node.value]


def construct_scalar_checked(loader: SafeLoaderNoDuplicates, node: yaml.ScalarNode) -> Any:
    check_tag(loader, node)
    return yaml.SafeLoader.construct_scalar(loader, node)


SafeLoaderNoDuplicates.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping_no_duplicates
)
SafeLoaderNoDuplicates.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG, construct_sequence_checked
)
SafeLoaderNoDuplicates.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG, construct_scalar_checked
)


def validate_structure(obj: Any, depth: int = 0, visited: set | None = None) -> None:
    if depth > 20:
        raise ValueError("Container depth exceeds maximum allowed limit")

    if visited is None:
        visited = set()

    if isinstance(obj, dict):
        obj_id = id(obj)
        if obj_id in visited:
            raise ValueError("Cyclic reference detected")
        visited.add(obj_id)

        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError("Mapping keys must be strings")
            if isinstance(v, (dict, list)):
                validate_structure(v, depth + 1, visited)
            else:
                validate_structure(v, depth, visited)

        visited.remove(obj_id)

    elif isinstance(obj, list):
        obj_id = id(obj)
        if obj_id in visited:
            raise ValueError("Cyclic reference detected")
        visited.add(obj_id)

        for item in obj:
            if isinstance(item, (dict, list)):
                validate_structure(item, depth + 1, visited)
            else:
                validate_structure(item, depth, visited)

        visited.remove(obj_id)

    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("Non-finite numbers are not allowed")
    elif isinstance(obj, (int, str, bool)) or obj is None:
        pass
    else:
        raise ValueError("Unsupported data type")


class ConfigInput(BaseModel):
    yaml: str


app = FastAPI()


@app.post("/configuracao", status_code=status.HTTP_200_OK)
def importar_configuracao(payload: ConfigInput) -> dict:
    raw_bytes = payload.yaml.encode("utf-8")
    if len(raw_bytes) > 16384:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload exceeds maximum allowed size",
        )

    try:
        docs = list(yaml.load_all(payload.yaml, Loader=SafeLoaderNoDuplicates))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YAML document",
        )

    if len(docs) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty YAML document is not allowed",
        )

    if len(docs) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple YAML documents are not allowed",
        )

    doc = docs[0]

    if not isinstance(doc, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration root must be a mapping",
        )

    try:
        validate_structure(doc, depth=0)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid configuration content",
        )

    return {"configuracao": doc}