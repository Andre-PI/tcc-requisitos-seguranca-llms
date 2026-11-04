from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
import yaml

app = FastAPI()


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., min_length=1)


def validar_raiz(objeto):
    if not isinstance(objeto, dict):
        raise ValueError("A raiz da configuracao deve ser um mapeamento YAML.")
    for chave in objeto.keys():
        if not isinstance(chave, str):
            raise ValueError("As chaves da raiz devem ser textuais.")
    return objeto


@app.post("/configuracao")
def importar_configuracao(entrada: ConfiguracaoEntrada):
    try:
        objeto = yaml.safe_load(entrada.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail="YAML invalido.") from exc

    try:
        configuracao = validar_raiz(objeto)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"configuracao": configuracao}