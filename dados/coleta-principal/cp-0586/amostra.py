from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
import yaml


app = FastAPI(title="Importador de Configuração YAML", version="1.0.0")


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    yaml: str = Field(..., min_length=1)


def _validate_structure(obj: Any, *, _depth: int = 0) -> Any:
    if _depth > 200:
        raise ValueError("Estrutura YAML excessivamente profunda.")

    if obj is None or isinstance(obj, (str, bool, int, float)):
        return obj

    if isinstance(obj, list):
        return [_validate_structure(item, _depth=_depth + 1) for item in obj]

    if isinstance(obj, dict):
        validated: dict[str, Any] = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                raise ValueError("A raiz e os mapeamentos devem conter apenas chaves textuais.")
            validated[key] = _validate_structure(value, _depth=_depth + 1)
        return validated

    raise ValueError(f"Tipo YAML nao suportado: {type(obj).__name__}")


def _load_yaml_safe(document: str) -> Any:
    try:
        loaded = yaml.safe_load(document)
    except yaml.YAMLError as exc:
        raise ValueError("Documento YAML invalido.") from exc

    if loaded is None:
        raise ValueError("Documento YAML vazio ou sem conteudo util.")

    if not isinstance(loaded, dict):
        raise ValueError("A raiz da configuracao deve ser um mapeamento.")

    return _validate_structure(loaded)


@app.post("/configuracao")
async def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    try:
        configuracao = _load_yaml_safe(payload.yaml)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"configuracao": configuracao}