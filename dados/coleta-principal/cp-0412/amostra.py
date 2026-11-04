from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from yaml.composer import Composer
from yaml.constructor import SafeConstructor
from yaml.loader import SafeLoader
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.resolver import Resolver


MAX_YAML_BYTES = 16384
MAX_DEPTH = 20

app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(...)

    @field_validator("yaml")
    @classmethod
    def validate_yaml_text(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("invalid")
        return v


class _StrictSafeLoader(SafeLoader):
    pass


_StrictSafeLoader.yaml_constructors = SafeConstructor.yaml_constructors.copy()
_StrictSafeLoader.yaml_multi_constructors = SafeConstructor.yaml_multi_constructors.copy()
_StrictSafeLoader.yaml_implicit_resolvers = Resolver.yaml_implicit_resolvers.copy()
_StrictSafeLoader.yaml_path_resolvers = {}
_StrictSafeLoader.add_constructor(None, SafeConstructor.construct_undefined)


def _count_bytes_utf8(text: str) -> int:
    return len(text.encode("utf-8"))


def _generic_400() -> HTTPException:
    return HTTPException(status_code=400, detail="Entrada invalida.")


def _generic_422() -> HTTPException:
    return HTTPException(status_code=422, detail="Entrada invalida.")


def _validate_scalar_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("invalid")
        return value
    raise ValueError("invalid")


def _validate_structure(value: Any, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        raise ValueError("invalid")

    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError("invalid")
            if k in out:
                raise ValueError("invalid")
            out[k] = _validate_structure(v, depth + 1)
        return out

    if isinstance(value, list):
        return [_validate_structure(item, depth + 1) for item in value]

    return _validate_scalar_value(value)


class _DepthAndAliasValidator:
    def __init__(self, root: Node):
        self.root = root
        self._seen_nodes: set[int] = set()
        self._active_nodes: set[int] = set()
        self._anchors: dict[str, Node] = {}

    def validate(self) -> None:
        self._visit(self.root, 0, True)

    def _visit(self, node: Node, depth: int, is_root: bool = False) -> None:
        if depth > MAX_DEPTH:
            raise ValueError("invalid")

        node_id = id(node)
        if node_id in self._active_nodes:
            raise ValueError("invalid")
        if node_id in self._seen_nodes:
            return

        self._seen_nodes.add(node_id)
        self._active_nodes.add(node_id)

        try:
            if getattr(node, "anchor", None):
                anchor = node.anchor
                if anchor in self._anchors and self._anchors[anchor] is not node:
                    raise ValueError("invalid")
                self._anchors[anchor] = node

            if isinstance(node, MappingNode):
                if is_root is False and depth >= MAX_DEPTH:
                    pass
                for key_node, value_node in node.value:
                    if not isinstance(key_node, ScalarNode) or key_node.tag != "tag:yaml.org,2002:str":
                        raise ValueError("invalid")
                    self._visit(key_node, depth + 1)
                    self._visit(value_node, depth + 1)
            elif isinstance(node, SequenceNode):
                for item in node.value:
                    self._visit(item, depth + 1)
            elif isinstance(node, ScalarNode):
                if node.tag.startswith("tag:yaml.org,2002:") and node.tag not in {
                    "tag:yaml.org,2002:str",
                    "tag:yaml.org,2002:int",
                    "tag:yaml.org,2002:float",
                    "tag:yaml.org,2002:bool",
                    "tag:yaml.org,2002:null",
                }:
                    raise ValueError("invalid")
                if node.tag.startswith("!"):
                    raise ValueError("invalid")
                if node.tag.startswith("tag:yaml.org,2002:python"):
                    raise ValueError("invalid")
            else:
                raise ValueError("invalid")
        finally:
            self._active_nodes.remove(node_id)


def _load_and_validate_yaml(text: str) -> dict[str, Any]:
    if _count_bytes_utf8(text) > MAX_YAML_BYTES:
        raise HTTPException(status_code=413, detail="Entrada invalida.")

    try:
        docs = list(yaml.compose_all(text, Loader=_StrictSafeLoader))
    except yaml.YAMLError as exc:
        raise _generic_400() from exc

    if len(docs) != 1:
        raise _generic_400()

    root = docs[0]
    if root is None:
        raise _generic_400()

    try:
        _DepthAndAliasValidator(root).validate()
    except ValueError as exc:
        raise _generic_400() from exc

    try:
        data = yaml.load(text, Loader=_StrictSafeLoader)
    except yaml.YAMLError as exc:
        raise _generic_400() from exc

    if data is None:
        raise _generic_400()

    try:
        validated = _validate_structure(data, 0)
    except ValueError as exc:
        raise _generic_400() from exc

    if not isinstance(validated, dict):
        raise _generic_400()

    return validated


@app.post("/configuracao")
async def importar_configuracao(payload: ConfiguracaoRequest):
    try:
        configuracao = _load_and_validate_yaml(payload.yaml)
    except ValidationError:
        raise _generic_422()
    return {"configuracao": configuracao}