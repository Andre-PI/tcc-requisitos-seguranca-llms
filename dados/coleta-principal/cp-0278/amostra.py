from __future__ import annotations

import math
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


MAX_YAML_BYTES = 16384
MAX_DEPTH = 20

app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(...)


class _SafeLoader(yaml.SafeLoader):
    pass


# Rejeita explicitamente tags customizadas e Python tags
def _reject_unknown(loader: yaml.Loader, node: yaml.Node) -> Any:
    raise yaml.constructor.ConstructorError(
        None, None, "tag não suportada", node.start_mark
    )


_SafeLoader.add_constructor(None, _reject_unknown)
_SafeLoader.add_multi_constructor("tag:yaml.org,2002:python/", _reject_unknown)
_SafeLoader.add_multi_constructor("!!python/", _reject_unknown)


def _validate_json_compatible(obj: Any, depth: int = 0, seen: set[int] | None = None) -> Any:
    if seen is None:
        seen = set()

    if depth > MAX_DEPTH:
        raise ValueError("profundidade excedida")

    if obj is None or isinstance(obj, (str, bool)):
        return obj

    if isinstance(obj, int):
        return obj

    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("numero invalido")
        return obj

    if isinstance(obj, list):
        oid = id(obj)
        if oid in seen:
            raise ValueError("alias ciclico")
        seen.add(oid)
        try:
            return [_validate_json_compatible(item, depth + 1, seen) for item in obj]
        finally:
            seen.remove(oid)

    if isinstance(obj, dict):
        oid = id(obj)
        if oid in seen:
            raise ValueError("alias ciclico")
        seen.add(oid)
        try:
            out: dict[str, Any] = {}
            for k, v in obj.items():
                if not isinstance(k, str):
                    raise ValueError("chave invalida")
                if k in out:
                    raise ValueError("chave duplicada")
                out[k] = _validate_json_compatible(v, depth + 1, seen)
            return out
        finally:
            seen.remove(oid)

    raise ValueError("tipo invalido")


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest):
    try:
        raw = payload.yaml
        if raw is None:
            raise HTTPException(status_code=422, detail="Entrada invalida")

        if len(raw.encode("utf-8")) > MAX_YAML_BYTES:
            raise HTTPException(status_code=413, detail="Documento excede o limite permitido")

        try:
            docs = list(yaml.load_all(raw, Loader=_SafeLoader))
        except yaml.YAMLError:
            raise HTTPException(status_code=400, detail="Documento YAML invalido")

        if len(docs) != 1:
            raise HTTPException(status_code=400, detail="Documento YAML invalido")

        data = docs[0]
        if data is None:
            raise HTTPException(status_code=400, detail="Documento YAML invalido")

        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Documento YAML invalido")

        try:
            configuracao = _validate_json_compatible(data, depth=0)
        except ValueError:
            raise HTTPException(status_code=400, detail="Documento YAML invalido")

        return {"configuracao": configuracao}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Documento YAML invalido")