from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any
import yaml

app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    yaml: str = Field(..., min_length=1)


def _validar_raiz(objeto: Any) -> dict:
    if not isinstance(objeto, dict):
        raise HTTPException(
            status_code=422,
            detail="A raiz da configuração deve ser um mapeamento YAML.",
        )

    for chave in objeto.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=422,
                detail="Todas as chaves da raiz da configuração devem ser textuais.",
            )

    return objeto


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest):
    try:
        objeto = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=f"YAML inválido: {exc}") from exc

    configuracao = _validar_raiz(objeto)
    return {"configuracao": configuracao}