from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Dict

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()


TOKEN_TTL_SECONDS = 900
TOKEN_BYTES = 32
HMAC_KEY = secrets.token_bytes(32)


@dataclass
class TokenRecord:
    usuario_id: int
    expires_at: float
    used: bool = False


_tokens: Dict[str, TokenRecord] = {}


def _hash_token(token: str) -> str:
    digest = hmac.new(HMAC_KEY, token.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii")


def _gerar_token() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(TOKEN_BYTES)).decode("ascii").rstrip("=")


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: SecretStr


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(str(payload.email))
    if usuario is not None:
        token = _gerar_token()
        token_hash = _hash_token(token)
        _tokens[token_hash] = TokenRecord(
            usuario_id=usuario["id"],
            expires_at=now := agora() + TOKEN_TTL_SECONDS,
            used=False,
        )
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha."}


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(payload: RedefinirSenhaRequest):
    token_hash = _hash_token(payload.token)
    record = _tokens.get(token_hash)

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token inválido.")

    if record.used:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token já utilizado.")

    if agora() >= record.expires_at:
        del _tokens[token_hash]
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token expirado.")

    definir_senha(record.usuario_id, payload.nova_senha.get_secret_value())
    record.used = True
    del _tokens[token_hash]

    return {"mensagem": "Senha redefinida com sucesso."}