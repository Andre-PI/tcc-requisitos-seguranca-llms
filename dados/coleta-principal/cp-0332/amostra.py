from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
import yaml


app = FastAPI(title="Importador de Configuração YAML")


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    yaml: str = Field(..., min_length=1)

    @field_validator("yaml")
    @classmethod
    def validar_yaml_nao_vazio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("O campo 'yaml' não pode estar vazio.")
        return v


class _SafeLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: yaml.Loader, node: yaml.Node, deep: bool = False) -> dict[str, Any]:
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            None, None, "Esperado um mapeamento YAML na raiz.", node.start_mark
        )

    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "A raiz da configuração deve conter apenas chaves textuais.",
                key_node.start_mark,
            )
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


_SafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


@app.post("/configuracao", status_code=status.HTTP_200_OK)
async def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    try:
        documento = yaml.load(payload.yaml, Loader=_SafeLoader)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YAML inválido.",
        ) from exc

    if not isinstance(documento, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A raiz da configuração deve ser um mapeamento com chaves textuais.",
        )

    for chave in documento.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A raiz da configuração deve conter apenas chaves textuais.",
            )

    return {"configuracao": documento}