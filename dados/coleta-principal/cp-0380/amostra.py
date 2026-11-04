from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()


class ConfiguracaoInput(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(dados: ConfiguracaoInput) -> Dict[str, Any]:
    try:
        conteudo = yaml.safe_load(dados.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Erro de sintaxe YAML: {exc}")

    if not isinstance(conteudo, dict):
        raise HTTPException(
            status_code=422,
            detail="A raiz da configuracao deve ser um mapeamento (dicionario).",
        )

    return {"configuracao": conteudo}