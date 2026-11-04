from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Dict, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field, SecretStr

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()

_TOKEN_TTL_SECONDS = 900
_TOKEN_BYTES = 32
_TOKEN_HASH_BYTES = 32

# token_hash -> (usuario_id, expira_em, usado)
_tokens: Dict[str, Tuple[int, float, bool]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: SecretStr = Field(min_length=1)


class MensagemResponse(BaseModel):
    mensagem: str


def _hash_token(token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _gerar_token() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(_TOKEN_BYTES)).decode("ascii").rstrip("=")


@app.post("/recuperar-senha", response_model=MensagemResponse)
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is not None:
        token = _gerar_token()
        token_hash = _hash_token(token)
        expira_em = float(agora()) + _TOKEN_TTL_SECONDS
        _tokens[token_hash] = (int(usuario["id"]), expira_em, False)
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha."}


@app.post("/redefinir-senha", response_model=MensagemResponse)
def redefinir_senha(payload: RedefinirSenhaRequest):
    token_hash = _hash_token(payload.token)
    registro = _tokens.get(token_hash)

    if registro is None:
        raise HTTPException(status_code=400, detail="Token inválido.")

    usuario_id, expira_em, usado = registro
    agora_atual = float(agora())

    if usado:
        raise HTTPException(status_code=410, detail="Token já utilizado.")

    if agora_atual >= expira_em:
        _tokens[token_hash] = (usuario_id, expira_em, True)
        raise HTTPException(status_code=410, detail="Token expirado.")

    definir_senha(usuario_id, payload.nova_senha.get_secret_value())
    _tokens[token_hash] = (usuario_id, expira_em, True)
    return {"mensagem": "Senha redefinida com sucesso."}