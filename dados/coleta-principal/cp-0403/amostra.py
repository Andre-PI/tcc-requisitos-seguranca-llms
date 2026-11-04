from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any
import yaml

app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    yaml: str = Field(..., description="Documento YAML como texto")


def _validar_raiz_mapeamento(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise HTTPException(
            status_code=400,
            detail="A raiz da configuracao deve ser um mapeamento YAML com chaves textuais.",
        )
    for chave in obj.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=400,
                detail="A raiz da configuracao deve conter apenas chaves textuais.",
            )
    return obj


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML invalido: {exc}") from exc

    configuracao = _validar_raiz_mapeamento(configuracao)
    return {"configuracao": configuracao}