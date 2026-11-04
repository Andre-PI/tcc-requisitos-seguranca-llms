from __future__ import annotations

import math
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from yaml.composer import ComposerError
from yaml.constructor import ConstructorError
from yaml.events import AliasEvent, DocumentEndEvent, DocumentStartEvent
from yaml.loader import SafeLoader
from yaml.nodes import MappingNode, ScalarNode, SequenceNode
from yaml.parser import ParserError
from yaml.reader import ReaderError
from yaml.resolver import BaseResolver
from yaml.scanner import ScannerError

app = FastAPI()


MAX_YAML_BYTES = 16384
MAX_DEPTH = 20


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str

    @field_validator("yaml")
    @classmethod
    def validar_nao_vazio(cls, v: str) -> str:
        if not isinstance(v, str) or v == "":
            raise ValueError("entrada invalida")
        return v


class StrictSafeLoader(SafeLoader):
    pass


StrictSafeLoader.yaml_implicit_resolvers = SafeLoader.yaml_implicit_resolvers.copy()
StrictSafeLoader.yaml_constructors = SafeLoader.yaml_constructors.copy()
StrictSafeLoader.yaml_multi_constructors = {}
StrictSafeLoader.add_constructor(None, lambda loader, node: (_ for _ in ()).throw(ConstructorError(None, None, "tag nao suportada", node.start_mark)))


def _erro_400() -> HTTPException:
    return HTTPException(status_code=400, detail="entrada invalida")


def _erro_413() -> HTTPException:
    return HTTPException(status_code=413, detail="entrada muito grande")


def _validar_finito(valor: Any) -> None:
    if isinstance(valor, float) and not math.isfinite(valor):
        raise _erro_400()


def _validar_profundidade(obj: Any, profundidade: int = 0, vistos: set[int] | None = None) -> None:
    if vistos is None:
        vistos = set()

    if profundidade > MAX_DEPTH:
        raise _erro_400()

    if isinstance(obj, dict):
        oid = id(obj)
        if oid in vistos:
            raise _erro_400()
        vistos.add(oid)
        for k, v in obj.items():
            if not isinstance(k, str):
                raise _erro_400()
            _validar_profundidade(v, profundidade + 1, vistos)
        vistos.remove(oid)
    elif isinstance(obj, list):
        oid = id(obj)
        if oid in vistos:
            raise _erro_400()
        vistos.add(oid)
        for item in obj:
            _validar_profundidade(item, profundidade + 1, vistos)
        vistos.remove(oid)
    elif obj is None or isinstance(obj, (str, bool, int)):
        return
    elif isinstance(obj, float):
        _validar_finito(obj)
    else:
        raise _erro_400()


def _validar_objeto_json(obj: Any) -> None:
    if not isinstance(obj, dict):
        raise _erro_400()

    for k, v in obj.items():
        if not isinstance(k, str):
            raise _erro_400()
        _validar_profundidade(v, 1)


def _checar_multiplo_documento_e_alias_ciclico(texto: str) -> None:
    try:
        eventos = yaml.parse(texto, Loader=SafeLoader)
        docs = 0
        for evento in eventos:
            if isinstance(evento, DocumentStartEvent):
                docs += 1
                if docs > 1:
                    raise _erro_400()
            elif isinstance(evento, AliasEvent):
                continue
        if docs == 0:
            raise _erro_400()
    except (ReaderError, ScannerError, ParserError, ComposerError, ConstructorError, yaml.YAMLError):
        raise _erro_400()


def _carregar_yaml_seguro(texto: str) -> Any:
    try:
        data = yaml.load(texto, Loader=StrictSafeLoader)
        if data is None:
            raise _erro_400()
        return data
    except (ReaderError, ScannerError, ParserError, ComposerError, ConstructorError, yaml.YAMLError, RecursionError, ValueError):
        raise _erro_400()


def _validar_sem_tags_customizadas(texto: str) -> None:
    try:
        for evento in yaml.parse(texto, Loader=SafeLoader):
            if hasattr(evento, "tag") and getattr(evento, "tag", None):
                tag = str(getattr(evento, "tag"))
                if tag.startswith("tag:yaml.org,2002:"):
                    continue
                raise _erro_400()
    except (ReaderError, ScannerError, ParserError, ComposerError, ConstructorError, yaml.YAMLError):
        raise _erro_400()


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoEntrada):
    try:
        tamanho = len(payload.yaml.encode("utf-8"))
    except UnicodeEncodeError:
        raise _erro_400()

    if tamanho > MAX_YAML_BYTES:
        raise _erro_413()

    texto = payload.yaml

    _checar_multiplo_documento_e_alias_ciclico(texto)
    _validar_sem_tags_customizadas(texto)

    try:
        obj = _carregar_yaml_seguro(texto)
    except HTTPException:
        raise
    except Exception:
        raise _erro_400()

    _validar_objeto_json(obj)

    return {"configuracao": obj}