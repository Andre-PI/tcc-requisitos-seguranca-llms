import math
from typing import Any
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()

MAX_BYTES = 16384
MAX_DEPTH = 20

ALLOWED_TAG_PREFIXES = ("tag:yaml.org,2002:",)
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
                "found duplicate key",
                key_node.start_mark,
            )
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_no_duplicates,
)


class ConfigRequest(BaseModel):
    yaml: str = Field(..., min_length=1)


def validate_structure(obj: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ValueError("Maximum nesting depth exceeded")

    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError("Mapping keys must be strings")
            validate_structure(v, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            validate_structure(item, depth + 1)
    elif isinstance(obj, (str, bool)) or obj is None:
        pass
    elif isinstance(obj, (int, float)):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("Numeric values must be finite")
    else:
        raise ValueError("Invalid data type encountered")


def check_nodes_and_aliases(loader: StrictSafeLoader) -> None:
    seen_anchors = set()

    def visit(node: yaml.Node, path_anchors: set):
        tag = node.tag
        if not tag.startswith("tag:yaml.org,2002:") or tag not in ALLOWED_TAGS:
            raise ValueError("Disallowed or custom YAML tag encountered")

        current_anchor = node.anchor
        if current_anchor:
            if current_anchor in path_anchors:
                raise ValueError("Cyclic alias detected")
            path_anchors = path_anchors | {current_anchor}
            seen_anchors.add(current_anchor)

        if isinstance(node, yaml.SequenceNode):
            for child in node.value:
                visit(child, path_anchors)
        elif isinstance(node, yaml.MappingNode):
            for key_node, value_node in node.value:
                visit(key_node, path_anchors)
                visit(value_node, path_anchors)

    root_node = loader.get_single_node()
    if root_node is None:
        raise ValueError("Document is empty")
    if not isinstance(root_node, yaml.MappingNode):
        raise ValueError("Root document must be a mapping")

    visit(root_node, set())
    loader.get_single_node = lambda: root_node


@app.post("/configuracao")
def importar_configuracao(req: ConfigRequest):
    content_bytes = req.yaml.encode("utf-8")
    if len(content_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload size limit exceeded",
        )

    try:
        loader = StrictSafeLoader(req.yaml)
        try:
            check_nodes_and_aliases(loader)
            data = loader.get_single_data()
        finally:
            loader.dispose()

        if data is None or not isinstance(data, dict):
            raise ValueError("Invalid configuration structure")

        validate_structure(data, depth=0)
    except yaml.YAMLError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YAML document",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid configuration content",
        )

    return {"configuracao": data}