from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
import yaml
from yaml.loader import SafeLoader


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., description="Documento YAML como texto")


app = FastAPI()


def _validar_raiz(objeto):
    if not isinstance(objeto, dict):
        raise ValueError("A raiz da configuração deve ser um mapeamento YAML.")
    for chave in objeto.keys():
        if not isinstance(chave, str):
            raise ValueError("Todas as chaves da raiz devem ser textuais.")


@app.post("/configuracao")
async def importar_configuracao(entrada: ConfiguracaoEntrada):
    try:
        objeto = yaml.load(entrada.yaml, Loader=SafeLoader)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML inválido: {exc}") from exc

    if objeto is None:
        objeto = {}

    try:
        _validar_raiz(objeto)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"configuracao": objeto}