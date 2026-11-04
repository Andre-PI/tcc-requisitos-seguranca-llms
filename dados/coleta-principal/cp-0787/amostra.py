from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()

memoria_configuracao: Any = None


class ConfigYAMLRequest(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(dados: ConfigYAMLRequest):
    global memoria_configuracao
    try:
        conteudo = yaml.safe_load(dados.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=400, detail=f"Erro ao processar YAML: {exc}"
        )

    memoria_configuracao = conteudo
    return {"configuracao": memoria_configuracao}