from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    yaml: str


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest):
    try:
        dados = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=422, detail=f"Erro ao processar YAML: {exc}"
        )

    if dados is None:
        dados = {}

    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=422,
            detail="A raiz da configuracao deve ser um mapeamento.",
        )

    return {"configuracao": dados}