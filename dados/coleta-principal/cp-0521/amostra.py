from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
import hashlib
import secrets
import hmac
from dataclasses import dataclass
from typing import Dict, Optional

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_TTL_SECONDS = 900
TOKEN_BYTES = 32


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


@dataclass
class TokenInfo:
    usuario_id: int
    token_hash: str
    expires_at: float
    used: bool = False


_tokens: Dict[str, TokenInfo] = {}


def _gerar_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is not None:
        token = _gerar_token()
        token_hash = _hash_token(token)
        _tokens[token_hash] = TokenInfo(
            usuario_id=usuario["id"],
            token_hash=token_hash,
            expires_at=agora() + TOKEN_TTL_SECONDS,
        )
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    token_hash = _hash_token(payload.token)
    info: Optional[TokenInfo] = _tokens.get(token_hash)

    if info is None:
        raise HTTPException(status_code=404, detail="Token inválido.")

    if info.used:
        raise HTTPException(status_code=410, detail="Token já utilizado.")

    if agora() >= info.expires_at:
        _tokens.pop(token_hash, None)
        raise HTTPException(status_code=410, detail="Token expirado.")

    definir_senha(info.usuario_id, payload.nova_senha)
    info.used = True
    _tokens.pop(token_hash, None)

    return {"mensagem": "Senha redefinida com sucesso."}