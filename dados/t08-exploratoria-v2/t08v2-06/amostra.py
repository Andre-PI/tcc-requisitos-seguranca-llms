from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
import yaml

app = FastAPI()


class ConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str


@app.post("/configuracao")
def importar_configuracao(payload: ConfiguracaoRequest):
    try:
        configuracao = yaml.safe_load(payload.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML inválido: {exc}") from exc

    if configuracao is None:
        configuracao = {}

    if not isinstance(configuracao, dict):
        raise HTTPException(
            status_code=400,
            detail="A raiz da configuração deve ser um mapeamento YAML.",
        )

    return {"configuracao": configuracao}