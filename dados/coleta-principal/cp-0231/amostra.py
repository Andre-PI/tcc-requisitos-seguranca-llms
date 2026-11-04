from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr, ConfigDict

from tcc_t05_infra import agora, enviar_email, definir_senha, usuario_por_email

app = FastAPI()


TOKEN_TTL_SECONDS = 15 * 60
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MIN_TOKEN_BYTES = 32


@dataclass
class ResetTokenRecord:
    usuario_id: int
    email: str
    expires_at: float


_tokens: Dict[str, ResetTokenRecord] = {}


class RecuperarSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class RecuperarSenhaResponse(BaseModel):
    mensagem: str


class RedefinirSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1)
    nova_senha: SecretStr = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class RedefinirSenhaResponse(BaseModel):
    mensagem: str


def _gerar_token() -> str:
    return secrets.token_urlsafe(MIN_TOKEN_BYTES)


def _limpar_tokens_expirados() -> None:
    atual = agora()
    expirados = [token for token, rec in _tokens.items() if rec.expires_at <= atual]
    for token in expirados:
        _tokens.pop(token, None)


@app.post("/recuperar-senha", response_model=RecuperarSenhaResponse, status_code=status.HTTP_200_OK)
def recuperar_senha(payload: RecuperarSenhaRequest) -> RecuperarSenhaResponse:
    _limpar_tokens_expirados()

    usuario = usuario_por_email(str(payload.email))
    mensagem = "Se o e-mail estiver cadastrado, um token de recuperação foi enviado."

    if usuario is None:
        return RecuperarSenhaResponse(mensagem=mensagem)

    token = _gerar_token()
    _tokens[token] = ResetTokenRecord(
        usuario_id=int(usuario["id"]),
        email=str(usuario["email"]),
        expires_at=agora() + TOKEN_TTL_SECONDS,
    )
    enviar_email(str(usuario["email"]), token)
    return RecuperarSenhaResponse(mensagem=mensagem)


@app.post("/redefinir-senha", response_model=RedefinirSenhaResponse, status_code=status.HTTP_200_OK)
def redefinir_senha(payload: RedefinirSenhaRequest) -> RedefinirSenhaResponse:
    _limpar_tokens_expirados()

    record = _tokens.get(payload.token)
    if record is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado.")

    nova_senha = payload.nova_senha.get_secret_value()
    definir_senha(record.usuario_id, nova_senha)
    _tokens.pop(payload.token, None)
    return RedefinirSenhaResponse(mensagem="Senha redefinida com sucesso.")