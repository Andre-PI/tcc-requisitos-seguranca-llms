from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()


TOKEN_TTL_SEGUNDOS = 15 * 60
TOKEN_TAMANHO_BYTES = 32


@dataclass
class TokenRecuperacao:
    usuario_id: int
    email_normalizado: str
    expira_em: float


_tokens_por_hash: Dict[str, TokenRecuperacao] = {}


def _normalizar_email(email: str) -> str:
    return email.strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _gerar_token() -> str:
    return secrets.token_urlsafe(TOKEN_TAMANHO_BYTES)


def _limpar_tokens_expirados() -> None:
    atual = agora()
    expirados = [
        token_hash
        for token_hash, dados in _tokens_por_hash.items()
        if dados.expira_em <= atual
    ]
    for token_hash in expirados:
        _tokens_por_hash.pop(token_hash, None)


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: EmailStr) -> EmailStr:
        return v


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    nova_senha: SecretStr = Field(min_length=8, max_length=256)

    @field_validator("token")
    @classmethod
    def validar_token(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("token inválido")
        return v

    @field_validator("nova_senha")
    @classmethod
    def validar_nova_senha(cls, v: SecretStr) -> SecretStr:
        senha = v.get_secret_value()
        if len(senha.strip()) < 8:
            raise ValueError("nova_senha inválida")
        return v


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    email_normalizado = _normalizar_email(str(payload.email))
    usuario = usuario_por_email(email_normalizado)

    if usuario is not None:
        token = _gerar_token()
        token_hash = _hash_token(token)
        _tokens_por_hash[token_hash] = TokenRecuperacao(
            usuario_id=int(usuario["id"]),
            email_normalizado=email_normalizado,
            expira_em=agora() + TOKEN_TTL_SEGUNDOS,
        )
        enviar_email(email_normalizado, token)

    return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação foi enviado."}


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    token = payload.token.strip()
    token_hash = _hash_token(token)
    dados = _tokens_por_hash.get(token_hash)

    if dados is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    if dados.expira_em <= agora():
        _tokens_por_hash.pop(token_hash, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    nova_senha = payload.nova_senha.get_secret_value()
    definir_senha(dados.usuario_id, nova_senha)
    _tokens_por_hash.pop(token_hash, None)

    return {"mensagem": "Senha redefinida com sucesso."}