from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Dict

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr, ConfigDict

from tcc_t05_infra import agora, enviar_email, definir_senha, usuario_por_email

app = FastAPI()


TOKEN_TTL_SEGUNDOS = 3600
TOKEN_BYTES = 32


@dataclass
class TokenRecuperacao:
    usuario_id: int
    email: str
    expira_em: float


_tokens_por_valor: Dict[str, TokenRecuperacao] = {}


class RecuperarSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=512)
    nova_senha: SecretStr = Field(min_length=8, max_length=256)


def _gerar_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    expirados = [token for token, dados in _tokens_por_valor.items() if dados.expira_em <= tempo_atual]
    for token in expirados:
        _tokens_por_valor.pop(token, None)


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    token = _gerar_token()
    _tokens_por_valor[token] = TokenRecuperacao(
        usuario_id=usuario["id"],
        email=usuario["email"],
        expira_em=agora() + TOKEN_TTL_SEGUNDOS,
    )

    enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação foi enviado."}


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    dados_token = _tokens_por_valor.get(payload.token)
    if dados_token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    if dados_token.expira_em <= agora():
        _tokens_por_valor.pop(payload.token, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    nova_senha = payload.nova_senha.get_secret_value()
    definir_senha(dados_token.usuario_id, nova_senha)

    _tokens_por_valor.pop(payload.token, None)

    return {"mensagem": "Senha redefinida com sucesso."}