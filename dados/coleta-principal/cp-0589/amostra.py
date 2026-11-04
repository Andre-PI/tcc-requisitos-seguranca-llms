from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator


app = FastAPI(title="Importador de Configuração YAML", version="1.0.0")


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    yaml: str = Field(..., min_length=1)

    @field_validator("yaml")
    @classmethod
    def validar_yaml(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("O campo 'yaml' deve ser uma string.")
        if not v.strip():
            raise ValueError("O campo 'yaml' não pode ser vazio.")
        return v


def _validar_chaves_textuais(obj: Any, caminho: str = "$") -> None:
    if isinstance(obj, dict):
        for chave, valor in obj.items():
            if not isinstance(chave, str):
                raise ValueError(f"Chave não textual encontrada em {caminho}: {chave!r}")
            _validar_chaves_textuais(valor, f"{caminho}.{chave}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _validar_chaves_textuais(item, f"{caminho}[{idx}]")
    elif isinstance(obj, (str, bool, int, float)) or obj is None:
        return
    else:
        raise ValueError(f"Tipo de valor não suportado em {caminho}: {type(obj).__name__}")


@app.post("/configuracao", status_code=200)
def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError:
        raise HTTPException(status_code=400, detail="YAML inválido.")

    if configuracao is None:
        raise HTTPException(status_code=400, detail="A configuração YAML deve conter um mapeamento na raiz.")

    if not isinstance(configuracao, dict):
        raise HTTPException(status_code=400, detail="A raiz da configuração deve ser um mapeamento.")

    try:
        _validar_chaves_textuais(configuracao)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"configuracao": configuracao}