from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()


TOKEN_TTL = 900.0
TOKEN_BYTES = 32


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


@dataclass
class TokenRecord:
    usuario_id: int
    token_hash: bytes
    criado_em: float
    usado: bool = False


_tokens: Dict[str, TokenRecord] = {}


def _gerar_token() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(TOKEN_BYTES)).rstrip(b"=").decode("ascii")


def _hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def _limpar_expirados() -> None:
    agora_atual = agora()
    expirados = [
        k for k, rec in _tokens.items()
        if (agora_atual - rec.criado_em) >= TOKEN_TTL
    ]
    for k in expirados:
        del _tokens[k]


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is not None:
        token = _gerar_token()
        _tokens[token] = TokenRecord(
            usuario_id=usuario["id"],
            token_hash=_hash_token(token),
            criado_em=agora(),
            usado=False,
        )
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_expirados()

    token = payload.token
    token_hash = _hash_token(token)

    encontrado: Optional[str] = None
    record: Optional[TokenRecord] = None

    for k, rec in _tokens.items():
        if hmac.compare_digest(rec.token_hash, token_hash):
            encontrado = k
            record = rec
            break

    if record is None:
        raise HTTPException(status_code=404, detail="Token inválido.")

    if record.usado:
        raise HTTPException(status_code=410, detail="Token já utilizado.")

    if (agora() - record.criado_em) >= TOKEN_TTL:
        del _tokens[encontrado]
        raise HTTPException(status_code=410, detail="Token expirado.")

    definir_senha(record.usuario_id, payload.nova_senha)
    record.usado = True
    del _tokens[encontrado]

    return {"mensagem": "Senha redefinida com sucesso."}