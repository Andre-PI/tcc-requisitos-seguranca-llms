from __future__ import annotations

import math
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from yaml.composer import Composer
from yaml.constructor import ConstructorError
from yaml.loader import SafeLoader
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


MAX_YAML_BYTES = 16384
MAX_DEPTH = 20

app = FastAPI()


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(min_length=1)

    @field_validator("yaml")
    @classmethod
    def validar_tamanho(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_YAML_BYTES:
            raise ValueError("Entrada muito grande")
        return v


class StrictSafeLoader(SafeLoader):
    pass


def _reject_undefined(loader: SafeLoader, node: yaml.Node) -> Any:
    raise ConstructorError(None, None, "Tag não permitida", node.start_mark)


StrictSafeLoader.add_constructor(None, _reject_undefined)


def _compose_single_document(text: str) -> yaml.Node:
    loader = StrictSafeLoader(text)
    try:
        try:
            node = loader.get_single_node()
        finally:
            loader.dispose()
    except yaml.YAMLError:
        raise HTTPException(status_code=400, detail="Documento YAML inválido")
    if node is None:
        raise HTTPException(status_code=400, detail="Documento YAML inválido")
    return node


def _validate_scalar(node: ScalarNode) -> Any:
    tag = node.tag
    value = node.value

    if tag == "tag:yaml.org,2002:str":
        return value
    if tag == "tag:yaml.org,2002:int":
        try:
            return int(value, 0)
        except Exception:
            raise HTTPException(status_code=400, detail="Documento YAML inválido")
    if tag == "tag:yaml.org,2002:float":
        try:
            num = float(value)
        except Exception:
            raise HTTPException(status_code=400, detail="Documento YAML inválido")
        if not math.isfinite(num):
            raise HTTPException(status_code=400, detail="Documento YAML inválido")
        return num
    if tag == "tag:yaml.org,2002:bool":
        if value.lower() in {"true", "yes", "on"}:
            return True
        if value.lower() in {"false", "no", "off"}:
            return False
        raise HTTPException(status_code=400, detail="Documento YAML inválido")
    if tag == "tag:yaml.org,2002:null":
        return None

    raise HTTPException(status_code=400, detail="Documento YAML inválido")


def _validate_node(node: yaml.Node, depth: int, seen: set[int]) -> Any:
    if depth > MAX_DEPTH:
        raise HTTPException(status_code=400, detail="Documento YAML inválido")

    node_id = id(node)
    if isinstance(node, (MappingNode, SequenceNode)):
        if node_id in seen:
            raise HTTPException(status_code=400, detail="Documento YAML inválido")
        seen.add(node_id)

    if isinstance(node, ScalarNode):
        if node.tag.startswith("tag:yaml.org,2002:"):
            return _validate_scalar(node)
        raise HTTPException(status_code=400, detail="Documento YAML inválido")

    if isinstance(node, SequenceNode):
        if node.tag != "tag:yaml.org,2002:seq":
            raise HTTPException(status_code=400, detail="Documento YAML inválido")
        return [_validate_node(item, depth + 1, seen) for item in node.value]

    if isinstance(node, MappingNode):
        if node.tag != "tag:yaml.org,2002:map":
            raise HTTPException(status_code=400, detail="Documento YAML inválido")
        result: dict[str, Any] = {}
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode) or key_node.tag != "tag:yaml.org,2002:str":
                raise HTTPException(status_code=400, detail="Documento YAML inválido")
            key = key_node.value
            if key in result:
                raise HTTPException(status_code=400, detail="Documento YAML inválido")
            result[key] = _validate_node(value_node, depth + 1, seen)
        return result

    raise HTTPException(status_code=400, detail="Documento YAML inválido")


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoEntrada):
    try:
        node = _compose_single_document(payload.yaml)
        configuracao = _validate_node(node, 0, set())
        if not isinstance(configuracao, dict):
            raise HTTPException(status_code=400, detail="Documento YAML inválido")
        return {"configuracao": configuracao}
    except ValidationError:
        raise HTTPException(status_code=422, detail="Entrada inválida")
    except HTTPException:
        raise
    except yaml.YAMLError:
        raise HTTPException(status_code=400, detail="Documento YAML inválido")
    except Exception:
        raise HTTPException(status_code=400, detail="Documento YAML inválido")