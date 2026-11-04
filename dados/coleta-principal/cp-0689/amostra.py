from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Any
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKENS: Dict[str, Dict[str, Any]] = {}
_TTL_SEGUNDOS = 3600


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    expirados = [token for token, dados in _TOKENS.items() if tempo_atual - dados["criado_em"] > _TTL_SEGUNDOS]
    for token in expirados:
        del _TOKENS[token]


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = secrets.token_urlsafe(32)
    _TOKENS[token] = {
        "usuario_id": usuario["id"],
        "criado_em": agora(),
    }

    enviar_email(str(payload.email), token)
    return {"mensagem": "Token de recuperação enviado por e-mail"}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    dados = _TOKENS.get(payload.token)
    if dados is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    definir_senha(dados["usuario_id"], payload.nova_senha)
    del _TOKENS[payload.token]

    return {"mensagem": "Senha redefinida com sucesso"}