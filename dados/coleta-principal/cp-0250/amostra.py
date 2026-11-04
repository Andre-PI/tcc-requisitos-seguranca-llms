from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
import yaml
from yaml import YAMLError


app = FastAPI(title="Importador de Configuração YAML", version="1.0.0")


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    yaml: str = Field(..., min_length=1, description="Documento YAML como texto")


def _validar_objeto(obj: Any) -> Any:
    if isinstance(obj, dict):
        resultado: dict[str, Any] = {}
        for chave, valor in obj.items():
            if not isinstance(chave, str):
                raise ValueError("A raiz e os mapeamentos devem conter apenas chaves textuais.")
            resultado[chave] = _validar_objeto(valor)
        return resultado

    if isinstance(obj, list):
        return [_validar_objeto(item) for item in obj]

    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    raise ValueError("Tipo YAML nao suportado na configuracao.")


@app.post("/configuracao")
def importar_configuracao(entrada: ConfiguracaoEntrada) -> dict[str, Any]:
    try:
        dados = yaml.safe_load(entrada.yaml)
    except YAMLError:
        raise HTTPException(status_code=400, detail="YAML invalido.")
    except Exception:
        raise HTTPException(status_code=400, detail="Nao foi possivel processar o YAML.")

    if dados is None:
        raise HTTPException(status_code=400, detail="A configuracao YAML nao pode ser vazia.")
    if not isinstance(dados, dict):
        raise HTTPException(status_code=400, detail="A raiz da configuracao deve ser um mapeamento.")

    try:
        configuracao = _validar_objeto(dados)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"configuracao": configuracao}