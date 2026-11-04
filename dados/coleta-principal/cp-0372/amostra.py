from __future__ import annotations

import math
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator


MAX_YAML_BYTES = 16_384
MAX_DEPTH = 20

app = FastAPI()


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str

    @field_validator("yaml")
    @classmethod
    def validar_yaml_str(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Entrada invalida.")
        if len(v.encode("utf-8")) > MAX_YAML_BYTES:
            raise ValueError("Entrada muito grande.")
        return v


class StrictSafeLoader(yaml.SafeLoader):
    pass


# Remove resolvers that can create Python-specific or unexpected typed objects via tags.
# SafeLoader already avoids Python object construction, but we additionally reject
# any explicit custom tags during composition by inspecting node tags.
StrictSafeLoader.yaml_constructors = dict(yaml.SafeLoader.yaml_constructors)
StrictSafeLoader.yaml_multi_constructors = dict(yaml.SafeLoader.yaml_multi_constructors)


def _compose_single_document(text: str) -> yaml.nodes.Node:
    loader = StrictSafeLoader(text)
    try:
        try:
            node = loader.get_single_node()
        except yaml.YAMLError:
            raise HTTPException(status_code=400, detail="Documento YAML invalido.")
        if node is None:
            raise HTTPException(status_code=400, detail="Documento YAML invalido.")
        return node
    finally:
        loader.dispose()


def _reject_custom_tags(node: yaml.nodes.Node) -> None:
    tag = getattr(node, "tag", None)
    if isinstance(tag, str) and tag.startswith("tag:yaml.org,2002:"):
        return
    if isinstance(tag, str) and tag.startswith("!!"):
        return
    if isinstance(tag, str) and tag.startswith("!"):
        raise HTTPException(status_code=400, detail="Documento YAML invalido.")

    if isinstance(node, yaml.nodes.MappingNode):
        for key_node, value_node in node.value:
            _reject_custom_tags(key_node)
            _reject_custom_tags(value_node)
    elif isinstance(node, yaml.nodes.SequenceNode):
        for item in node.value:
            _reject_custom_tags(item)


def _depth_of_node(node: Any, current_depth: int = 0) -> int:
    if isinstance(node, dict):
        if current_depth > MAX_DEPTH:
            raise HTTPException(status_code=422, detail="Estrutura YAML muito profunda.")
        max_seen = current_depth
        for value in node.values():
            max_seen = max(max_seen, _depth_of_node(value, current_depth + 1))
        return max_seen
    if isinstance(node, list):
        if current_depth > MAX_DEPTH:
            raise HTTPException(status_code=422, detail="Estrutura YAML muito profunda.")
        max_seen = current_depth
        for item in node:
            max_seen = max(max_seen, _depth_of_node(item, current_depth + 1))
        return max_seen
    return current_depth


def _validate_json_compatible(value: Any, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        raise HTTPException(status_code=422, detail="Estrutura YAML muito profunda.")

    if value is None or isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise HTTPException(status_code=422, detail="Valor numerico invalido.")
        return value

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return [_validate_json_compatible(item, depth + 1) for item in value]

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise HTTPException(status_code=422, detail="Chave invalida.")
            out[k] = _validate_json_compatible(v, depth + 1)
        return out

    raise HTTPException(status_code=422, detail="Valor YAML invalido.")


def _load_yaml_to_python(text: str) -> Any:
    node = _compose_single_document(text)
    _reject_custom_tags(node)
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        raise HTTPException(status_code=400, detail="Documento YAML invalido.")
    if data is None:
        raise HTTPException(status_code=400, detail="Documento YAML invalido.")
    return data


def _validate_root_mapping(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Raiz invalida.")
    for key in data.keys():
        if not isinstance(key, str):
            raise HTTPException(status_code=422, detail="Chave invalida.")
    return data


@app.post("/configuracao")
def importar_configuracao(entrada: ConfiguracaoEntrada) -> dict[str, Any]:
    if len(entrada.yaml.encode("utf-8")) > MAX_YAML_BYTES:
        raise HTTPException(status_code=413, detail="Entrada muito grande.")

    data = _load_yaml_to_python(entrada.yaml)
    data = _validate_root_mapping(data)
    configuracao = _validate_json_compatible(data, depth=0)
    _depth_of_node(configuracao, current_depth=0)
    return {"configuracao": configuracao}