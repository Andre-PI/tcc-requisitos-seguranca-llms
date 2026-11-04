from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()

_estado_configuracao: Any = None


class ConfigYAMLRequest(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(dados: ConfigYAMLRequest) -> dict[str, Any]:
    global _estado_configuracao
    try:
        conteudo = yaml.safe_load(dados.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"YAML inválido: {exc}"
        ) from exc

    _estado_configuracao = conteudo
    return {"configuracao": _estado_configuracao}