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
    def validar_yaml(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("O campo 'yaml' deve ser uma string.")
        if not value.strip():
            raise ValueError("O campo 'yaml' nao pode estar vazio.")
        return value


class _LoaderSeguro(yaml.SafeLoader):
    pass


def _carregar_yaml_seguro(texto: str) -> Any:
    try:
        dados = yaml.load(texto, Loader=_LoaderSeguro)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail="YAML invalido.") from exc

    if dados is None:
        raise HTTPException(status_code=400, detail="A configuracao YAML nao pode ser nula.")

    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=400,
            detail="A raiz da configuracao deve ser um mapeamento com chaves textuais.",
        )

    for chave in dados.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=400,
                detail="A raiz da configuracao deve conter apenas chaves textuais.",
            )

    return dados


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoEntrada) -> dict[str, Any]:
    configuracao = _carregar_yaml_seguro(payload.yaml)
    return {"configuracao": configuracao}