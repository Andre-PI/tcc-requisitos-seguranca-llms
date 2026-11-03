from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

app = FastAPI(title="Importador de Configuração YAML")


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    yaml: str = Field(..., min_length=1)

    @field_validator("yaml")
    @classmethod
    def validar_yaml_nao_vazio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("O campo 'yaml' não pode estar vazio.")
        return v


def _validar_e_normalizar_objeto(objeto: Any) -> Any:
    if isinstance(objeto, dict):
        resultado: dict[str, Any] = {}
        for chave, valor in objeto.items():
            if not isinstance(chave, str):
                raise ValueError("A raiz da configuração deve ser um mapeamento com chaves textuais.")
            resultado[chave] = _validar_e_normalizar_objeto(valor)
        return resultado

    if isinstance(objeto, list):
        return [_validar_e_normalizar_objeto(item) for item in objeto]

    if isinstance(objeto, (str, bool, int, float)) or objeto is None:
        return objeto

    raise ValueError("A configuração contém um tipo de valor não suportado.")


def _carregar_yaml_seguro(documento: str) -> Any:
    try:
        return yaml.safe_load(documento)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail="YAML inválido.") from exc


@app.post("/configuracao")
def importar_configuracao(entrada: ConfiguracaoEntrada) -> dict[str, Any]:
    objeto = _carregar_yaml_seguro(entrada.yaml)

    if objeto is None:
        raise HTTPException(
            status_code=400,
            detail="A raiz da configuração deve ser um mapeamento com chaves textuais.",
        )

    if not isinstance(objeto, dict):
        raise HTTPException(
            status_code=400,
            detail="A raiz da configuração deve ser um mapeamento com chaves textuais.",
        )

    try:
        configuracao = _validar_e_normalizar_objeto(objeto)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"configuracao": configuracao}