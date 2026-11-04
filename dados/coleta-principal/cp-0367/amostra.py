from __future__ import annotations

import math
from typing import Any

import yaml
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from yaml.constructor import ConstructorError
from yaml.loader import SafeLoader
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


MAX_YAML_BYTES = 16384
MAX_DEPTH = 20

app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., min_length=1)

    @field_validator("yaml")
    @classmethod
    def _validate_yaml_text(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_YAML_BYTES:
            raise ValueError("too_large")
        return v


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_json_compatible(obj: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ValueError("too_deep")

    if obj is None or isinstance(obj, (str, bool)):
        return

    if _is_finite_number(obj):
        return

    if isinstance(obj, list):
        for item in obj:
            _validate_json_compatible(item, depth + 1)
        return

    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError("invalid_key")
            _validate_json_compatible(v, depth + 1)
        return

    raise ValueError("invalid_type")


def _construct_object(node, loader: SafeLoader, depth: int = 0):
    if depth > MAX_DEPTH:
        raise ValueError("too_deep")

    if isinstance(node, ScalarNode):
        if node.tag not in (
            "tag:yaml.org,2002:str",
            "tag:yaml.org,2002:bool",
            "tag:yaml.org,2002:int",
            "tag:yaml.org,2002:float",
            "tag:yaml.org,2002:null",
        ):
            raise ConstructorError(None, None, "unsupported tag", node.start_mark)
        value = loader.construct_object(node, deep=False)
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non_finite")
        return value

    if isinstance(node, SequenceNode):
        if node.tag != "tag:yaml.org,2002:seq":
            raise ConstructorError(None, None, "unsupported tag", node.start_mark)
        return [_construct_object(child, loader, depth + 1) for child in node.value]

    if isinstance(node, MappingNode):
        if node.tag != "tag:yaml.org,2002:map":
            raise ConstructorError(None, None, "unsupported tag", node.start_mark)
        result = {}
        seen_keys = set()
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode) or key_node.tag != "tag:yaml.org,2002:str":
                raise ValueError("invalid_key")
            key = loader.construct_object(key_node, deep=False)
            if not isinstance(key, str):
                raise ValueError("invalid_key")
            if key in seen_keys:
                raise ValueError("duplicate_key")
            seen_keys.add(key)
            result[key] = _construct_object(value_node, loader, depth + 1)
        return result

    raise ValueError("invalid_node")


def _load_yaml_single_document(text: str) -> Any:
    class StrictLoader(SafeLoader):
        pass

    def _forbid_undefined(loader, node):
        raise ConstructorError(None, None, "unsupported tag", node.start_mark)

    StrictLoader.add_constructor(None, _forbid_undefined)

    docs = list(yaml.compose_all(text, Loader=StrictLoader))
    if len(docs) != 1:
        raise ValueError("multiple_or_empty_documents")

    root = docs[0]
    if root is None:
        raise ValueError("empty_document")
    if not isinstance(root, MappingNode):
        raise ValueError("root_must_be_mapping")
    if root.tag != "tag:yaml.org,2002:map":
        raise ConstructorError(None, None, "unsupported tag", root.start_mark)

    loader = StrictLoader(text)
    try:
        obj = _construct_object(root, loader, depth=0)
    finally:
        loader.dispose()

    if not isinstance(obj, dict):
        raise ValueError("root_must_be_mapping")
    return obj


@app.post("/configuracao")
async def importar_configuracao(payload: ConfiguracaoRequest):
    try:
        configuracao = _load_yaml_single_document(payload.yaml)
        _validate_json_compatible(configuracao, depth=0)
        return JSONResponse(status_code=200, content={"configuracao": configuracao})
    except ValidationError:
        return JSONResponse(status_code=422, content={"detail": "Requisicao invalida."})
    except ValueError as exc:
        code = str(exc)
        if code == "too_large":
            return JSONResponse(status_code=413, content={"detail": "Conteudo excede o limite permitido."})
        return JSONResponse(status_code=400, content={"detail": "Configuracao invalida."})
    except (yaml.YAMLError, ConstructorError):
        return JSONResponse(status_code=400, content={"detail": "Configuracao invalida."})