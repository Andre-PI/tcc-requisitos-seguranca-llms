from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
import yaml

app = FastAPI()


class ImportacaoConfiguracaoRequest(BaseModel):
    yaml: str
    model_config = ConfigDict(extra="forbid")


@app.post("/configuracao")
def importar_configuracao(payload: ImportacaoConfiguracaoRequest):
    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML invalido: {exc}") from exc

    return {"configuracao": configuracao}