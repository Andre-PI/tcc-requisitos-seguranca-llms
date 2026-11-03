from __future__ import annotations

import math
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator


app = FastAPI()


MAX_YAML_BYTES = 16384
MAX_DEPTH = 20


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str

    @field_validator("yaml")
    @classmethod
    def validar_yaml_str(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Campo inválido")
        if len(v.encode("utf-8")) > MAX_YAML_BYTES:
            raise ValueError("Documento excede o limite")
        return v


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_structure(value: Any, depth: int, seen: set[int]) -> None:
    if depth > MAX_DEPTH:
        raise ValueError("Estrutura excede a profundidade permitida")

    if value is None or isinstance(value, (str, bool)) or _is_finite_number(value):
        return

    if isinstance(value, list):
        obj_id = id(value)
        if obj_id in seen:
            raise ValueError("Estrutura cíclica não permitida")
        seen.add(obj_id)
        try:
            for item in value:
                _validate_structure(item, depth + 1, seen)
        finally:
            seen.remove(obj_id)
        return

    if isinstance(value, dict):
        obj_id = id(value)
        if obj_id in seen:
            raise ValueError("Estrutura cíclica não permitida")
        seen.add(obj_id)
        try:
            for k, v in value.items():
                if not isinstance(k, str):
                    raise ValueError("Chave inválida")
                _validate_structure(v, depth + 1, seen)
        finally:
            seen.remove(obj_id)
        return

    raise ValueError("Tipo inválido")


def _reject_duplicate_keys(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode, deep: bool = False):
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


class StrictSafeLoader(yaml.SafeLoader):
    pass


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _reject_duplicate_keys,
)


def _parse_yaml_document(text: str) -> Any:
    try:
        docs = list(yaml.load_all(text, Loader=StrictSafeLoader))
    except yaml.YAMLError as exc:
        raise ValueError("Documento YAML inválido") from exc

    if not docs:
        raise ValueError("Documento vazio")
    if len(docs) != 1:
        raise ValueError("Múltiplos documentos não permitidos")

    data = docs[0]
    if not isinstance(data, dict):
        raise ValueError("Raiz inválida")
    return data


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoEntrada):
    if len(payload.yaml.encode("utf-8")) > MAX_YAML_BYTES:
        raise HTTPException(status_code=413, detail="Documento excede o limite")

    try:
        configuracao = _parse_yaml_document(payload.yaml)
        _validate_structure(configuracao, 0, set())
    except ValueError:
        raise HTTPException(status_code=400, detail="Entrada inválida")
    except yaml.YAMLError:
        raise HTTPException(status_code=400, detail="Entrada inválida")

    return {"configuracao": configuracao}