from __future__ import annotations

import math
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.resolver import Resolver


app = FastAPI()


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., min_length=1)

    @field_validator("yaml")
    @classmethod
    def validar_tamanho(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 16384:
            raise ValueError("arquivo YAML excede o limite permitido")
        return v


class StrictSafeLoader(yaml.SafeLoader):
    pass


StrictSafeLoader.yaml_implicit_resolvers = {
    k: [r for r in v if r[0] not in ("tag:yaml.org,2002:timestamp",)]
    for k, v in Resolver.yaml_implicit_resolvers.items()
}

for ch in list(StrictSafeLoader.yaml_implicit_resolvers.keys()):
    StrictSafeLoader.yaml_implicit_resolvers[ch] = [
        r for r in StrictSafeLoader.yaml_implicit_resolvers[ch]
        if r[0] not in (
            "tag:yaml.org,2002:python/name",
            "tag:yaml.org,2002:python/module",
            "tag:yaml.org,2002:python/object",
            "tag:yaml.org,2002:python/object/new",
            "tag:yaml.org,2002:python/object/apply",
        )
    ]


def _raise_generic() -> None:
    raise HTTPException(status_code=400, detail="Documento YAML inválido")


def _check_finite_number(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _raise_generic()


def _validate_structure(value: Any, depth: int, seen: set[int]) -> None:
    if depth > 20:
        _raise_generic()

    if isinstance(value, dict):
        obj_id = id(value)
        if obj_id in seen:
            _raise_generic()
        seen.add(obj_id)
        for k, v in value.items():
            if not isinstance(k, str):
                _raise_generic()
            _validate_structure(v, depth + 1, seen)
        seen.remove(obj_id)
        return

    if isinstance(value, list):
        obj_id = id(value)
        if obj_id in seen:
            _raise_generic()
        seen.add(obj_id)
        for item in value:
            _validate_structure(item, depth + 1, seen)
        seen.remove(obj_id)
        return

    if value is None or isinstance(value, (str, bool, int)):
        return

    if isinstance(value, float):
        _check_finite_number(value)
        return

    _raise_generic()


def _construct_mapping(loader: yaml.Loader, node: MappingNode, deep: bool = False) -> dict[str, Any]:
    if not isinstance(node, MappingNode):
        raise ConstructorError(None, None, "expected a mapping node", node.start_mark)
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        if not isinstance(key_node, ScalarNode) or key_node.tag != "tag:yaml.org,2002:str":
            raise ConstructorError(None, None, "mapping keys must be strings", key_node.start_mark)
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ConstructorError(None, None, "mapping keys must be strings", key_node.start_mark)
        if key in mapping:
            raise ConstructorError(None, None, "duplicate key", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@app.post("/configuracao")
def importar_configuracao(entrada: ConfiguracaoEntrada) -> dict[str, Any]:
    if len(entrada.yaml.encode("utf-8")) > 16384:
        raise HTTPException(status_code=413, detail="Arquivo YAML excede o limite permitido")

    try:
        documentos = list(yaml.load_all(entrada.yaml, Loader=StrictSafeLoader))
    except yaml.YAMLError:
        _raise_generic()

    if len(documentos) != 1:
        _raise_generic()

    configuracao = documentos[0]

    if not isinstance(configuracao, dict):
        _raise_generic()

    _validate_structure(configuracao, 0, set())

    return {"configuracao": configuracao}