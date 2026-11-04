from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

app = FastAPI(title="Importador de Configuracao YAML", version="1.0.0")


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    yaml: str = Field(..., min_length=1)

    @field_validator("yaml")
    @classmethod
    def validar_yaml_nao_vazio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("O campo 'yaml' não pode estar vazio.")
        return v


def _validar_estruturas(obj: Any, *, nivel: int = 0, max_nivel: int = 1000) -> None:
    if nivel > max_nivel:
        raise ValueError("Estrutura YAML muito profunda.")

    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError("A raiz e os mapeamentos aninhados devem usar chaves textuais.")
            _validar_estruturas(v, nivel=nivel + 1, max_nivel=max_nivel)
    elif isinstance(obj, list):
        for item in obj:
            _validar_estruturas(item, nivel=nivel + 1, max_nivel=max_nivel)
    elif isinstance(obj, (str, bool, int, float)) or obj is None:
        return
    else:
        raise ValueError(f"Tipo YAML não suportado: {type(obj).__name__}")


def _importar_yaml(texto_yaml: str) -> dict[str, Any]:
    try:
        documento = yaml.safe_load(texto_yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail="YAML inválido.") from exc

    if documento is None:
        raise HTTPException(status_code=400, detail="O YAML deve conter um mapeamento na raiz.")

    if not isinstance(documento, dict):
        raise HTTPException(status_code=400, detail="A raiz da configuração deve ser um mapeamento.")

    for chave in documento.keys():
        if not isinstance(chave, str):
            raise HTTPException(status_code=400, detail="A raiz da configuração deve usar chaves textuais.")

    try:
        _validar_estruturas(documento)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return documento


@app.post("/configuracao")
def configuracao(entrada: ConfiguracaoEntrada) -> dict[str, Any]:
    configuracao_importada = _importar_yaml(entrada.yaml)
    return {"configuracao": configuracao_importada}