from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from typing import Dict

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr, model_validator

from tcc_t05_infra import agora, enviar_email, definir_senha, usuario_por_email


app = FastAPI()


TOKEN_TTL_SEGUNDOS = 15 * 60
TOKEN_TAMANHO_BYTES = 32


@dataclass(frozen=True)
class TokenRecuperacao:
    usuario_id: int
    email: str
    criado_em: float


_tokens_por_token: Dict[str, TokenRecuperacao] = {}
_lock = threading.RLock()


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    nova_senha: SecretStr

    @model_validator(mode="after")
    def validar_nova_senha(self):
        senha = self.nova_senha.get_secret_value()
        if len(senha) < 8:
            raise ValueError("nova_senha deve ter ao menos 8 caracteres")
        return self


def _gerar_token() -> str:
    return secrets.token_urlsafe(TOKEN_TAMANHO_BYTES)


def _limpar_tokens_expirados() -> None:
    limite = agora() - TOKEN_TTL_SEGUNDOS
    with _lock:
        expirados = [t for t, info in _tokens_por_token.items() if info.criado_em < limite]
        for token in expirados:
            _tokens_por_token.pop(token, None)


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is None:
        return {"mensagem": "Se o e-mail estiver cadastrado, você receberá um token de recuperação."}

    _limpar_tokens_expirados()
    token = _gerar_token()
    info = TokenRecuperacao(usuario_id=usuario["id"], email=usuario["email"], criado_em=agora())

    with _lock:
        _tokens_por_token[token] = info

    enviar_email(usuario["email"], token)
    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá um token de recuperação."}


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    with _lock:
        info = _tokens_por_token.pop(payload.token, None)

    if info is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado.")

    definir_senha(info.usuario_id, payload.nova_senha.get_secret_value())
    return {"mensagem": "Senha redefinida com sucesso."}