from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
import hashlib
import secrets
from dataclasses import dataclass
from typing import Dict

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
class TokenRecord:
    usuario_id: int
    expires_at: float
    used: bool = False


_tokens: Dict[str, TokenRecord] = {}


def _gerar_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _resumo_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is not None:
        token = _gerar_token()
        token_hash = _resumo_token(token)
        _tokens[token_hash] = TokenRecord(
            usuario_id=usuario["id"],
            expires_at=agora() + TOKEN_TTL_SECONDS,
            used=False,
        )
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail existir em nossa base, enviaremos instruções de recuperação de senha."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    token_hash = _resumo_token(payload.token)
    registro = _tokens.get(token_hash)

    if registro is None:
        raise HTTPException(status_code=404, detail="Token inválido.")
    if registro.used:
        raise HTTPException(status_code=410, detail="Token já utilizado.")
    if agora() >= registro.expires_at:
        _tokens.pop(token_hash, None)
        raise HTTPException(status_code=410, detail="Token expirado.")

    definir_senha(registro.usuario_id, payload.nova_senha)
    registro.used = True
    _tokens.pop(token_hash, None)

    return {"mensagem": "Senha redefinida com sucesso."}