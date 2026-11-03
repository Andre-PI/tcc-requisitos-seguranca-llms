from __future__ import annotations

import secrets
import string
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()

TOKEN_TTL_SEGUNDOS = 15 * 60
TOKEN_TAMANHO = 32
MAX_TENTATIVAS_REDEFINICAO = 5

# Estrutura em memória:
# token -> {"usuario_id": int, "email": str, "expira_em": float, "tentativas": int}
tokens_ativos: Dict[str, Dict[str, object]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr = Field(..., examples=["usuario@exemplo.com"])


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=256)
    nova_senha: SecretStr = Field(..., min_length=8, max_length=256)


def _gerar_token() -> str:
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(TOKEN_TAMANHO))


def _limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    expirados = [
        token
        for token, dados in tokens_ativos.items()
        if float(dados["expira_em"]) <= tempo_atual
    ]
    for token in expirados:
        tokens_ativos.pop(token, None)


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(str(payload.email))
    if usuario is None:
        return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha."}

    token = _gerar_token()
    while token in tokens_ativos:
        token = _gerar_token()

    tokens_ativos[token] = {
        "usuario_id": int(usuario["id"]),
        "email": str(usuario["email"]),
        "expira_em": agora() + TOKEN_TTL_SEGUNDOS,
        "tentativas": 0,
    }

    enviar_email(str(usuario["email"]), token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha."}


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    token = payload.token.strip()
    dados = tokens_ativos.get(token)

    if not dados:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    if float(dados["expira_em"]) <= agora():
        tokens_ativos.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    tentativas = int(dados["tentativas"])
    if tentativas >= MAX_TENTATIVAS_REDEFINICAO:
        tokens_ativos.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Solicite um novo token.",
        )

    usuario_id = int(dados["usuario_id"])
    nova_senha = payload.nova_senha.get_secret_value()

    definir_senha(usuario_id, nova_senha)

    tokens_ativos.pop(token, None)

    return {"mensagem": "Senha redefinida com sucesso."}