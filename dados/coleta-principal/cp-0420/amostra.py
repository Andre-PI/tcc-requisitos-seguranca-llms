from __future__ import annotations

from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validar_yaml_nao_vazio(self) -> "ConfiguracaoRequest":
        if not self.yaml.strip():
            raise ValueError("O campo 'yaml' nao pode estar vazio.")
        return self


def _validar_e_normalizar(objeto: Any) -> Any:
    if isinstance(objeto, dict):
        for chave in objeto.keys():
            if not isinstance(chave, str):
                raise ValueError("A raiz da configuracao e seus mapeamentos devem usar chaves textuais.")
        return {chave: _validar_e_normalizar(valor) for chave, valor in objeto.items()}

    if isinstance(objeto, list):
        return [_validar_e_normalizar(item) for item in objeto]

    if isinstance(objeto, (str, bool, int, float)) or objeto is None:
        return objeto

    raise ValueError(f"Tipo YAML nao suportado: {type(objeto).__name__}")


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    try:
        documento = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail="YAML invalido.") from exc

    if documento is None:
        raise HTTPException(status_code=400, detail="A configuracao YAML deve ser um mapeamento na raiz.")

    if not isinstance(documento, dict):
        raise HTTPException(status_code=400, detail="A raiz da configuracao deve ser um mapeamento.")

    try:
        configuracao = _validar_e_normalizar(documento)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"configuracao": configuracao}