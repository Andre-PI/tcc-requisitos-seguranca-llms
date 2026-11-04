from typing import Any
import yaml
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()

# Limite para prevenir ataques de negação de serviço (DoS / Billion Laughs / payload excessivo)
MAX_YAML_LENGTH = 1_000_000  # 1 MB


class ConfiguracaoRequest(BaseModel):
    yaml: str = Field(..., max_length=MAX_YAML_LENGTH)


class ConfiguracaoResponse(BaseModel):
    configuracao: dict[str, Any]


def validar_chaves_str(dados: Any) -> None:
    """Valida recursivamente se todas as chaves de mapeamentos são strings."""
    if isinstance(dados, dict):
        for k, v in dados.items():
            if not isinstance(k, str):
                raise ValueError(f"Chave do mapeamento deve ser texto: {k!r}")
            validar_chaves_str(v)
    elif isinstance(dados, list):
        for item in dados:
            validar_chaves_str(item)


@app.post(
    "/configuracao",
    response_model=ConfiguracaoResponse,
    status_code=status.HTTP_200_OK,
)
def importar_configuracao(payload: ConfiguracaoRequest) -> dict[str, Any]:
    yaml_text = payload.yaml

    # Uso do yaml.SafeLoader para mitigar RCE e deserialização insegura (OWASP A08:2021)
    try:
        conteudo = yaml.load(yaml_text, Loader=yaml.SafeLoader)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro de sintaxe YAML: {exc}",
        )

    # A raiz da configuração deve ser um mapeamento (dicionário)
    if not isinstance(conteudo, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A raiz da configuração deve ser um mapeamento (objeto/dicionário).",
        )

    # Validação de conformidade das chaves como texto
    try:
        validar_chaves_str(conteudo)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return {"configuracao": conteudo}