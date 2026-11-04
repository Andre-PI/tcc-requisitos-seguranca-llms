from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()

TOKEN_TTL_SECONDS = 900
TOKEN_BYTES = 32


@dataclass
class TokenRecord:
    usuario_id: int
    expires_at: float
    used: bool = False


_tokens: Dict[str, TokenRecord] = {}
_lock = threading.Lock()


def _gerar_token() -> str:
    raw = secrets.token_bytes(TOKEN_BYTES)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _limpar_expirados_locked(now: float) -> None:
    expirados = [
        token_hash
        for token_hash, record in _tokens.items()
        if record.expires_at <= now
    ]
    for token_hash in expirados:
        del _tokens[token_hash]


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(str(payload.email))
    if usuario is not None:
        token = _gerar_token()
        token_hash = _hash_token(token)
        now = agora()
        with _lock:
            _limpar_expirados_locked(now)
            _tokens[token_hash] = TokenRecord(
                usuario_id=int(usuario["id"]),
                expires_at=now + TOKEN_TTL_SECONDS,
                used=False,
            )
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    now = agora()
    token_hash = _hash_token(payload.token)

    with _lock:
        _limpar_expirados_locked(now)
        record = _tokens.get(token_hash)

        if record is None:
            raise HTTPException(status_code=400, detail="Token inválido")
        if record.used:
            raise HTTPException(status_code=410, detail="Token já utilizado")
        if record.expires_at <= now:
            del _tokens[token_hash]
            raise HTTPException(status_code=410, detail="Token expirado")

        record.used = True
        usuario_id = record.usuario_id
        del _tokens[token_hash]

    definir_senha(usuario_id, payload.nova_senha)
    return {"mensagem": "Senha redefinida com sucesso."}