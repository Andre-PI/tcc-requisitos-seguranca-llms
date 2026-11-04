from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator


app = FastAPI(title="Importador de Configuração YAML")


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    yaml: str = Field(..., min_length=1)

    @field_validator("yaml")
    @classmethod
    def validar_yaml(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("O campo 'yaml' não pode estar vazio.")
        return value


class SafeLoaderWithLimits(yaml.SafeLoader):
    pass


def _compose_node_limits(loader: yaml.Loader, parent: yaml.nodes.Node | None, index: Any) -> yaml.nodes.Node:
    return yaml.SafeLoader.compose_node(loader, parent, index)


def _construct_mapping(loader: yaml.Loader, node: yaml.nodes.MappingNode, deep: bool = False) -> dict[str, Any]:
    mapping = yaml.SafeLoader.construct_mapping(loader, node, deep=deep)
    for key in mapping.keys():
        if not isinstance(key, str):
            raise ValueError("A raiz da configuração e as chaves aninhadas devem ser mapeamentos com chaves textuais.")
    return mapping


SafeLoaderWithLimits.compose_node = _compose_node_limits  # type: ignore[method-assign]
SafeLoaderWithLimits.construct_mapping = _construct_mapping  # type: ignore[method-assign]


def _load_yaml_document(yaml_text: str) -> Any:
    try:
        data = yaml.load(yaml_text, Loader=SafeLoaderWithLimits)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail="YAML inválido.") from exc

    if data is None:
        raise HTTPException(status_code=400, detail="O documento YAML não pode ser vazio.")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="A raiz da configuração deve ser um mapeamento com chaves textuais.")
    for key in data.keys():
        if not isinstance(key, str):
            raise HTTPException(status_code=400, detail="A raiz da configuração deve ser um mapeamento com chaves textuais.")
    return data


@app.post("/configuracao", status_code=200)
def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    configuracao = _load_yaml_document(payload.yaml)
    return {"configuracao": configuracao}