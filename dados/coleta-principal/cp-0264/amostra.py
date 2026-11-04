from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Any
import yaml

app = FastAPI()


class ConfiguracaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str = Field(..., description="Documento YAML como texto")


def _validar_raiz(objeto: Any) -> dict[str, Any]:
    if not isinstance(objeto, dict):
        raise HTTPException(
            status_code=422,
            detail="A raiz da configuração deve ser um mapeamento YAML com chaves textuais.",
        )

    for chave in objeto.keys():
        if not isinstance(chave, str):
            raise HTTPException(
                status_code=422,
                detail="Todas as chaves da raiz devem ser textuais (strings).",
            )

    return objeto


@app.post("/configuracao")
def importar_configuracao(entrada: ConfiguracaoEntrada) -> dict[str, Any]:
    try:
        objeto = yaml.safe_load(entrada.yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=f"YAML inválido: {exc}") from exc

    objeto = _validar_raiz(objeto)
    return {"configuracao": objeto}