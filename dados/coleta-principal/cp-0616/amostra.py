from __future__ import annotations

import secrets
from typing import Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()

# Token store in memory:
# token -> (usuario_id, email, expires_at)
_TOKEN_TTL_SECONDS = 15 * 60
_tokens: Dict[str, Tuple[int, str, float]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    nova_senha: SecretStr

    @field_validator("token")
    @classmethod
    def token_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("token inválido")
        return v

    @field_validator("nova_senha")
    @classmethod
    def senha_valida(cls, v: SecretStr) -> SecretStr:
        senha = v.get_secret_value()
        if len(senha) < 8:
            raise ValueError("nova_senha deve ter ao menos 8 caracteres")
        return v


def _limpar_tokens_expirados() -> None:
    now = agora()
    expirados = [t for t, (_, _, exp) in _tokens.items() if exp <= now]
    for t in expirados:
        _tokens.pop(t, None)


def _gerar_token() -> str:
    return secrets.token_urlsafe(32)


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(payload.email)
    mensagem = (
        "Se o e-mail informado estiver cadastrado, você receberá instruções para redefinir a senha."
    )

    if usuario is None:
        return {"mensagem": mensagem}

    token = _gerar_token()
    _tokens[token] = (int(usuario["id"]), str(usuario["email"]), agora() + _TOKEN_TTL_SECONDS)

    enviar_email(usuario["email"], token)
    return {"mensagem": mensagem}


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    token = payload.token
    registro = _tokens.get(token)
    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    usuario_id, _, _ = registro

    definir_senha(usuario_id, payload.nova_senha.get_secret_value())
    _tokens.pop(token, None)

    return {"mensagem": "Senha redefinida com sucesso."}