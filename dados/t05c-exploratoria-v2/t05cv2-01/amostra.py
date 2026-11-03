from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr, ConfigDict

from tcc_t05_infra import agora, enviar_email, definir_senha, usuario_por_email

app = FastAPI()

TOKEN_TTL_SECONDS = 15 * 60
TOKEN_BYTES = 32


@dataclass
class TokenRecord:
    usuario_id: int
    email: str
    criado_em: float


_tokens: Dict[str, TokenRecord] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr

    model_config = ConfigDict(extra="forbid")


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    nova_senha: SecretStr = Field(min_length=8)

    model_config = ConfigDict(extra="forbid")


def _gerar_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _limpar_tokens_expirados() -> None:
    limite = agora() - TOKEN_TTL_SECONDS
    expirados = [token for token, rec in _tokens.items() if rec.criado_em < limite]
    for token in expirados:
        del _tokens[token]


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(str(payload.email))
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado",
        )

    token = _gerar_token()
    _tokens[token] = TokenRecord(
        usuario_id=usuario["id"],
        email=usuario["email"],
        criado_em=agora(),
    )
    enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    record = _tokens.get(payload.token)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalido ou expirado",
        )

    definir_senha(record.usuario_id, payload.nova_senha.get_secret_value())
    del _tokens[payload.token]

    return {"mensagem": "Senha redefinida com sucesso."}