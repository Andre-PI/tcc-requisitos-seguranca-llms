from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()


TOKEN_TTL_SEGUNDOS = 3600.0


@dataclass
class TokenRecuperacao:
    usuario_id: int
    email: str
    expiracao: float


_tokens: Dict[str, TokenRecuperacao] = {}
_lock = threading.Lock()


class RecuperarSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados(agora_atual: float) -> None:
    expirados = [token for token, dados in _tokens.items() if dados.expiracao <= agora_atual]
    for token in expirados:
        _tokens.pop(token, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(str(payload.email))
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = secrets.token_urlsafe(32)
    tempo_atual = agora()

    with _lock:
        _limpar_tokens_expirados(tempo_atual)
        _tokens[token] = TokenRecuperacao(
            usuario_id=int(usuario["id"]),
            email=str(usuario["email"]),
            expiracao=tempo_atual + TOKEN_TTL_SEGUNDOS,
        )

    enviar_email(str(usuario["email"]), token)
    return {"mensagem": "Token de recuperação enviado por e-mail"}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    tempo_atual = agora()

    with _lock:
        _limpar_tokens_expirados(tempo_atual)
        dados = _tokens.pop(payload.token, None)

    if dados is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    definir_senha(dados.usuario_id, payload.nova_senha)
    return {"mensagem": "Senha redefinida com sucesso"}