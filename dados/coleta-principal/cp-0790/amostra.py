from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()


class YamlPayload(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(payload: YamlPayload) -> Dict[str, Any]:
    try:
        dados = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=422, detail=f"Erro ao processar YAML: {str(exc)}"
        )

    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=422,
            detail="A raiz da configuração deve ser um mapeamento.",
        )

    return {"configuracao": dados}