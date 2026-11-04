from __future__ import annotations

import secrets
from typing import Dict, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field, SecretStr, ConfigDict

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()

_TOKENS: Dict[str, Tuple[int, float]] = {}
_TTL_SEGUNDOS = 15 * 60


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: SecretStr = Field(min_length=1)


class MensagemResponse(BaseModel):
    mensagem: str

    model_config = ConfigDict(extra="forbid")


def _limpar_tokens_expirados() -> None:
    limite = agora()
    expirados = [token for token, (_, expira_em) in _TOKENS.items() if expira_em <= limite]
    for token in expirados:
        _TOKENS.pop(token, None)


@app.post("/recuperar-senha", response_model=MensagemResponse)
def recuperar_senha(payload: RecuperarSenhaRequest) -> dict:
    _limpar_tokens_expirados()
    usuario = usuario_por_email(payload.email)
    if usuario is None:
        return {"mensagem": "Se o e-mail estiver cadastrado, você receberá um token de recuperação."}

    token = secrets.token_urlsafe(32)
    _TOKENS[token] = (usuario["id"], agora() + _TTL_SEGUNDOS)
    enviar_email(usuario["email"], token)
    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá um token de recuperação."}


@app.post("/redefinir-senha", response_model=MensagemResponse)
def redefinir_senha(payload: RedefinirSenhaRequest) -> dict:
    _limpar_tokens_expirados()
    registro = _TOKENS.get(payload.token)
    if registro is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    usuario_id, expira_em = registro
    if expira_em <= agora():
        _TOKENS.pop(payload.token, None)
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    definir_senha(usuario_id, payload.nova_senha.get_secret_value())
    _TOKENS.pop(payload.token, None)
    return {"mensagem": "Senha redefinida com sucesso."}