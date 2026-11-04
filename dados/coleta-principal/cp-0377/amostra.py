from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
import yaml

app = FastAPI()

_configuracao_em_memoria = None


class ImportacaoConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str


@app.post("/configuracao")
def importar_configuracao(payload: ImportacaoConfiguracaoRequest):
    global _configuracao_em_memoria
    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML invalido: {exc}") from exc

    _configuracao_em_memoria = configuracao
    return {"configuracao": configuracao}