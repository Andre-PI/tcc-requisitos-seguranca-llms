from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()

_TOKEN_TTL_SECONDS = 15 * 60
_MAX_TOKEN_ATTEMPTS = 5
_MIN_PASSWORD_LENGTH = 8


@dataclass
class _TokenRecord:
    usuario_id: int
    email: str
    expires_at: float
    attempts: int = 0


_tokens: dict[str, _TokenRecord] = {}
_tokens_lock = threading.Lock()


class RecuperarSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr = Field(..., min_length=3, max_length=254)


class RedefinirSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    token: str = Field(..., min_length=16, max_length=256)
    nova_senha: str = Field(..., min_length=_MIN_PASSWORD_LENGTH, max_length=1024)


def _gerar_token() -> str:
    return secrets.token_urlsafe(32)


def _limpar_tokens_expirados() -> None:
    now = agora()
    with _tokens_lock:
        expirados = [token for token, rec in _tokens.items() if rec.expires_at <= now or rec.attempts >= _MAX_TOKEN_ATTEMPTS]
        for token in expirados:
            _tokens.pop(token, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest) -> dict[str, str]:
    _limpar_tokens_expirados()

    usuario = usuario_por_email(payload.email)
    if usuario is None:
        return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação será enviado."}

    token = _gerar_token()
    record = _TokenRecord(
        usuario_id=int(usuario["id"]),
        email=str(usuario["email"]),
        expires_at=agora() + _TOKEN_TTL_SECONDS,
    )

    with _tokens_lock:
        _tokens[token] = record

    try:
        enviar_email(record.email, token)
    except Exception:
        with _tokens_lock:
            _tokens.pop(token, None)
        raise HTTPException(status_code=500, detail="Falha ao enviar o e-mail de recuperação.")

    return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação será enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest) -> dict[str, str]:
    _limpar_tokens_expirados()

    with _tokens_lock:
        record = _tokens.get(payload.token)
        if record is None:
            raise HTTPException(status_code=400, detail="Token inválido ou expirado.")
        if record.expires_at <= agora() or record.attempts >= _MAX_TOKEN_ATTEMPTS:
            _tokens.pop(payload.token, None)
            raise HTTPException(status_code=400, detail="Token inválido ou expirado.")
        record.attempts += 1

    try:
        definir_senha(record.usuario_id, payload.nova_senha)
    except Exception:
        raise HTTPException(status_code=500, detail="Falha ao redefinir a senha.")

    with _tokens_lock:
        _tokens.pop(payload.token, None)

    return {"mensagem": "Senha redefinida com sucesso."}