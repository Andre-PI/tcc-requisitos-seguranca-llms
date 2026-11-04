from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from yaml.constructor import SafeConstructor
from yaml.loader import SafeLoader


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


class LoaderSeguroYAML(SafeLoader):
    pass


def _bloquear_construtor_inesperado(loader: SafeLoader, node: yaml.Node) -> Any:
    raise yaml.constructor.ConstructorError(
        None,
        None,
        "Tags YAML personalizadas não são permitidas.",
        node.start_mark,
    )


LoaderSeguroYAML.add_constructor(None, _bloquear_construtor_inesperado)


def _validar_objeto_configuracao(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("A raiz da configuração deve ser um mapeamento YAML.")
    for chave in obj.keys():
        if not isinstance(chave, str):
            raise ValueError("Todas as chaves da raiz devem ser textuais (strings).")
    return obj


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoEntrada) -> dict[str, Any]:
    try:
        configuracao = yaml.load(payload.yaml, Loader=LoaderSeguroYAML)
    except yaml.YAMLError:
        raise HTTPException(status_code=400, detail="YAML inválido.")
    except Exception:
        raise HTTPException(status_code=400, detail="Não foi possível importar a configuração.")

    try:
        configuracao = _validar_objeto_configuracao(configuracao)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"configuracao": configuracao}