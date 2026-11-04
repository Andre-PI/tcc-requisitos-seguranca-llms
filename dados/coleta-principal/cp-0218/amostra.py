from __future__ import annotations

import math
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from yaml.composer import ComposerError
from yaml.constructor import ConstructorError
from yaml.parser import ParserError
from yaml.reader import ReaderError
from yaml.scanner import ScannerError
from yaml.tokens import AliasToken, AnchorToken, BlockEndToken, BlockEntryToken, BlockMappingStartToken, BlockSequenceStartToken, DocumentEndToken, DocumentStartToken, FlowEntryToken, FlowMappingEndToken, FlowSequenceEndToken, KeyToken, ScalarToken, TagToken, ValueToken

app = FastAPI()


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(...)

    @field_validator("yaml")
    @classmethod
    def validar_yaml(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Entrada invalida")
        if len(v.encode("utf-8")) > 16384:
            raise ValueError("Entrada muito grande")
        return v


def _erro(status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail="Entrada invalida")


def _validate_node(node: Any, depth: int, seen: set[int]) -> None:
    if depth > 20:
        raise _erro(400)

    if isinstance(node, dict):
        obj_id = id(node)
        if obj_id in seen:
            raise _erro(400)
        seen.add(obj_id)
        for k, v in node.items():
            if not isinstance(k, str):
                raise _erro(400)
            _validate_node(v, depth + 1, seen)
        seen.remove(obj_id)
        return

    if isinstance(node, list):
        obj_id = id(node)
        if obj_id in seen:
            raise _erro(400)
        seen.add(obj_id)
        for item in node:
            _validate_node(item, depth + 1, seen)
        seen.remove(obj_id)
        return

    if node is None or isinstance(node, (str, bool)):
        return

    if isinstance(node, int) and not isinstance(node, bool):
        return

    if isinstance(node, float):
        if not math.isfinite(node):
            raise _erro(400)
        return

    raise _erro(400)


def _load_yaml_strict(text: str) -> Any:
    try:
        docs = list(yaml.load_all(text, Loader=yaml.SafeLoader))
    except (ReaderError, ScannerError, ParserError, ComposerError, ConstructorError, yaml.YAMLError):
        raise _erro(400)

    if not docs:
        raise _erro(400)
    if len(docs) != 1:
        raise _erro(400)

    return docs[0]


def _check_no_custom_or_python_tags(text: str) -> None:
    try:
        for token in yaml.scan(text):
            if isinstance(token, TagToken):
                raise _erro(400)
    except (ReaderError, ScannerError, ParserError, yaml.YAMLError):
        raise _erro(400)


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoEntrada) -> dict[str, Any]:
    try:
        _check_no_custom_or_python_tags(payload.yaml)
        data = _load_yaml_strict(payload.yaml)
    except HTTPException:
        raise
    except Exception:
        raise _erro(400)

    if not isinstance(data, dict):
        raise _erro(400)

    for k in data.keys():
        if not isinstance(k, str):
            raise _erro(400)

    _validate_node(data, 0, set())
    return {"configuracao": data}