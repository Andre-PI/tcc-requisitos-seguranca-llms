from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from yaml.constructor import ConstructorError
from yaml.loader import SafeLoader
from yaml.nodes import MappingNode, ScalarNode, SequenceNode
from yaml.composer import ComposerError


MAX_YAML_BYTES = 16_384
MAX_DEPTH = 20

app = FastAPI()


class ConfiguracaoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., min_length=1)

    @field_validator("yaml")
    @classmethod
    def validar_tamanho(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_YAML_BYTES:
            raise ValueError("yaml too large")
        return v


class StrictSafeLoader(SafeLoader):
    def construct_undefined(self, node):
        raise ConstructorError(None, None, "unsupported tag", node.start_mark)


StrictSafeLoader.add_constructor(None, StrictSafeLoader.construct_undefined)


def _load_single_document(texto: str) -> Any:
    try:
        docs = list(yaml.compose_all(texto, Loader=StrictSafeLoader))
    except ComposerError as exc:
        raise HTTPException(status_code=400, detail="Entrada YAML invalida.") from exc
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail="Entrada YAML invalida.") from exc

    if not docs:
        raise HTTPException(status_code=400, detail="Entrada YAML invalida.")
    if len(docs) != 1:
        raise HTTPException(status_code=400, detail="Entrada YAML invalida.")

    node = docs[0]
    if node is None:
        raise HTTPException(status_code=400, detail="Entrada YAML invalida.")

    try:
        return _construct_node(node, depth=0, seen=set())
    except (ConstructorError, ValueError, TypeError, RecursionError):
        raise HTTPException(status_code=400, detail="Entrada YAML invalida.") from None


def _construct_node(node, depth: int, seen: set[int]) -> Any:
    if depth > MAX_DEPTH:
        raise ValueError("max depth exceeded")

    if isinstance(node, ScalarNode):
        if node.tag.startswith("tag:yaml.org,2002:"):
            if node.tag == "tag:yaml.org,2002:str":
                return node.value
            if node.tag == "tag:yaml.org,2002:int":
                return int(node.value)
            if node.tag == "tag:yaml.org,2002:float":
                value = float(node.value)
                if not math.isfinite(value):
                    raise ValueError("non-finite number")
                return value
            if node.tag == "tag:yaml.org,2002:bool":
                return node.value.lower() in {"y", "yes", "true", "on"}
            if node.tag == "tag:yaml.org,2002:null":
                return None
            raise ValueError("unsupported tag")
        raise ValueError("unsupported tag")

    if isinstance(node, SequenceNode):
        obj_id = id(node)
        if obj_id in seen:
            raise ValueError("cyclic alias")
        seen.add(obj_id)
        try:
            return [_construct_node(item, depth + 1, seen) for item in node.value]
        finally:
            seen.remove(obj_id)

    if isinstance(node, MappingNode):
        obj_id = id(node)
        if obj_id in seen:
            raise ValueError("cyclic alias")
        seen.add(obj_id)
        try:
            out: dict[str, Any] = {}
            for key_node, value_node in node.value:
                key = _construct_node(key_node, depth + 1, seen)
                if not isinstance(key, str):
                    raise ValueError("non-string key")
                if key in out:
                    raise ValueError("duplicate key")
                out[key] = _construct_node(value_node, depth + 1, seen)
            return out
        finally:
            seen.remove(obj_id)

    raise ValueError("unsupported node")


def _validate_json_compatible(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ValueError("max depth exceeded")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_compatible(item, depth + 1)
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError("non-string key")
            _validate_json_compatible(v, depth + 1)
        return
    raise ValueError("unsupported value")


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoIn):
    if len(payload.yaml.encode("utf-8")) > MAX_YAML_BYTES:
        raise HTTPException(status_code=413, detail="Entrada YAML muito grande.")

    configuracao = _load_single_document(payload.yaml)

    if not isinstance(configuracao, dict):
        raise HTTPException(status_code=400, detail="Entrada YAML invalida.")

    _validate_json_compatible(configuracao, depth=0)
    return {"configuracao": configuracao}