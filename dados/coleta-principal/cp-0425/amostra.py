from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any
import yaml

app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    yaml: str = Field(..., min_length=1)


def _validar_raiz(objeto: Any) -> dict:
    if not isinstance(objeto, dict):
        raise ValueError("A raiz da configuracao deve ser um mapeamento YAML.")
    for chave in objeto.keys():
        if not isinstance(chave, str):
            raise ValueError("Todas as chaves da raiz devem ser textuais.")
    return objeto


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest):
    try:
        objeto = yaml.safe_load(payload.yaml)
        configuracao = _validar_raiz(objeto)
        return {"configuracao": configuracao}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML invalido: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc