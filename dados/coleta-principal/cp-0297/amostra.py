from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field, SecretStr, ConfigDict

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()


TOKEN_TTL_SEGUNDOS = 3600
TOKEN_TAMANHO_BYTES = 32


@dataclass(frozen=True)
class TokenRecuperacao:
    usuario_id: int
    email: str
    criado_em: float


_tokens_por_token: Dict[str, TokenRecuperacao] = {}


class RecuperarSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=256)
    nova_senha: SecretStr = Field(min_length=8, max_length=256)


def _limpar_tokens_expirados() -> None:
    agora_atual = agora()
    expirados = [
        token
        for token, dados in _tokens_por_token.items()
        if agora_atual - dados.criado_em > TOKEN_TTL_SEGUNDOS
    ]
    for token in expirados:
        _tokens_por_token.pop(token, None)


def _gerar_token() -> str:
    return secrets.token_urlsafe(TOKEN_TAMANHO_BYTES)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(str(payload.email))
    if usuario is not None:
        token = _gerar_token()
        _tokens_por_token[token] = TokenRecuperacao(
            usuario_id=int(usuario["id"]),
            email=str(usuario["email"]),
            criado_em=agora(),
        )
        enviar_email(str(usuario["email"]), token)

    return {"mensagem": "Se o e-mail estiver cadastrado, instruções de recuperação foram enviadas."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    dados_token = _tokens_por_token.pop(payload.token, None)
    if dados_token is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    nova_senha = payload.nova_senha.get_secret_value()
    definir_senha(dados_token.usuario_id, nova_senha)

    return {"mensagem": "Senha redefinida com sucesso."}