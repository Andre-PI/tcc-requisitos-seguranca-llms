from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()


TOKEN_TTL_SECONDS = 900


class RecuperarSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


@dataclass
class TokenInfo:
    usuario_id: int
    expires_at: float
    used: bool = False


_token_lock = Lock()
_tokens: Dict[str, TokenInfo] = {}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _gerar_token() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")


def _limpar_expirados(atual: float) -> None:
    expirados = [digest for digest, info in _tokens.items() if info.expires_at <= atual or info.used]
    for digest in expirados:
        _tokens.pop(digest, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)

    if usuario is not None:
        token = _gerar_token()
        digest = _hash_token(token)
        with _token_lock:
            _limpar_expirados(agora())
            _tokens[digest] = TokenInfo(
                usuario_id=usuario["id"],
                expires_at=agora() + TOKEN_TTL_SECONDS,
                used=False,
            )
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail informado estiver cadastrado, você receberá instruções para redefinir a senha."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    digest = _hash_token(payload.token)
    current = agora()

    with _token_lock:
        info = _tokens.get(digest)
        if info is None:
            raise HTTPException(status_code=404, detail="Token inválido.")
        if info.used:
            raise HTTPException(status_code=410, detail="Token já utilizado.")
        if current >= info.expires_at:
            _tokens.pop(digest, None)
            raise HTTPException(status_code=410, detail="Token expirado.")

        usuario_id = info.usuario_id
        info.used = True
        _tokens.pop(digest, None)

    definir_senha(usuario_id, payload.nova_senha)
    return {"mensagem": "Senha redefinida com sucesso."}