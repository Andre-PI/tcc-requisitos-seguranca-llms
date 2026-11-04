from __future__ import annotations

import math
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from pydantic.types import StrictStr
from yaml.composer import ComposerError
from yaml.constructor import ConstructorError
from yaml.events import AliasEvent
from yaml.loader import SafeLoader
from yaml.nodes import MappingNode, ScalarNode, SequenceNode
from yaml.parser import ParserError
from yaml.reader import ReaderError
from yaml.resolver import BaseResolver
from yaml.scanner import ScannerError


app = FastAPI()


MAX_YAML_BYTES = 16384
MAX_DEPTH = 20


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: StrictStr = Field(..., description="Documento YAML como texto")

    @field_validator("yaml")
    @classmethod
    def validar_tamanho(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_YAML_BYTES:
            raise ValueError("payload too large")
        return v


class NoTagSafeLoader(SafeLoader):
    pass


def _forbid_unknown_tags(loader: SafeLoader, tag_suffix: str, node: yaml.Node) -> Any:
    raise ConstructorError(None, None, "unsupported tag", node.start_mark)


NoTagSafeLoader.add_multi_constructor("!", _forbid_unknown_tags)
NoTagSafeLoader.add_multi_constructor("tag:yaml.org,2002:", _forbid_unknown_tags)
NoTagSafeLoader.add_multi_constructor("tag:yaml.org,2002:python/", _forbid_unknown_tags)


def _load_single_document(yaml_text: str) -> Any:
    try:
        docs = list(yaml.load_all(yaml_text, Loader=NoTagSafeLoader))
    except (ScannerError, ParserError, ReaderError, ComposerError, ConstructorError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Documento YAML inválido")
    except Exception:
        raise HTTPException(status_code=400, detail="Documento YAML inválido")

    if len(docs) != 1:
        raise HTTPException(status_code=400, detail="Documento YAML inválido")
    return docs[0]


def _validate_finite_number(value: Any) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise HTTPException(status_code=400, detail="Documento YAML inválido")
        return
    raise HTTPException(status_code=400, detail="Documento YAML inválido")


def _validate_structure(value: Any, depth: int = 0, seen: set[int] | None = None) -> Any:
    if seen is None:
        seen = set()

    if depth > MAX_DEPTH:
        raise HTTPException(status_code=400, detail="Documento YAML inválido")

    if isinstance(value, dict):
        obj_id = id(value)
        if obj_id in seen:
            raise HTTPException(status_code=400, detail="Documento YAML inválido")
        seen.add(obj_id)

        out: dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise HTTPException(status_code=400, detail="Documento YAML inválido")
            if k in out:
                raise HTTPException(status_code=400, detail="Documento YAML inválido")
            out[k] = _validate_structure(v, depth + 1, seen)
        seen.remove(obj_id)
        return out

    if isinstance(value, list):
        obj_id = id(value)
        if obj_id in seen:
            raise HTTPException(status_code=400, detail="Documento YAML inválido")
        seen.add(obj_id)

        out_list = [_validate_structure(item, depth + 1, seen) for item in value]
        seen.remove(obj_id)
        return out_list

    _validate_finite_number(value)
    return value


def _reject_alias_cycles_and_unknown_tags(yaml_text: str) -> None:
    try:
        events = yaml.parse(yaml_text, Loader=NoTagSafeLoader)
        for event in events:
            if isinstance(event, AliasEvent):
                continue
            if getattr(event, "tag", None):
                tag = event.tag
                if tag and not (
                    tag.startswith("tag:yaml.org,2002:")
                    and not tag.startswith("tag:yaml.org,2002:python/")
                ):
                    raise HTTPException(status_code=400, detail="Documento YAML inválido")
    except (ScannerError, ParserError, ReaderError, ComposerError, ConstructorError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Documento YAML inválido")
    except Exception:
        raise HTTPException(status_code=400, detail="Documento YAML inválido")


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    if len(payload.yaml.encode("utf-8")) > MAX_YAML_BYTES:
        raise HTTPException(status_code=413, detail="Payload muito grande")

    _reject_alias_cycles_and_unknown_tags(payload.yaml)
    data = _load_single_document(payload.yaml)

    if data is None:
        raise HTTPException(status_code=400, detail="Documento YAML inválido")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Documento YAML inválido")

    configuracao = _validate_structure(data, depth=0)

    return {"configuracao": configuracao}