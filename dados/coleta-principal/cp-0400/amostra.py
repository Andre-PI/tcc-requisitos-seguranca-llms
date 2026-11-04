from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
import secrets
import hashlib
import hmac
from dataclasses import dataclass
from typing import Dict, Optional

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_TTL_SEGUNDOS = 900
TOKEN_BYTES = 32


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


@dataclass
class TokenResetSenha:
    usuario_id: int
    token_hash: str
    criado_em: float
    usado: bool = False


_tokens: Dict[str, TokenResetSenha] = {}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _gerar_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _token_expirado(registro: TokenResetSenha, instante_atual: float) -> bool:
    return instante_atual >= (registro.criado_em + TOKEN_TTL_SEGUNDOS)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)

    if usuario is not None:
        token = _gerar_token()
        token_hash = _hash_token(token)
        _tokens[token_hash] = TokenResetSenha(
            usuario_id=usuario["id"],
            token_hash=token_hash,
            criado_em=agora(),
            usado=False,
        )
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    token_hash = _hash_token(payload.token)
    registro: Optional[TokenResetSenha] = _tokens.get(token_hash)

    if registro is None:
        raise HTTPException(status_code=404, detail="Token inválido.")

    if registro.usado:
        raise HTTPException(status_code=410, detail="Token já utilizado.")

    instante_atual = agora()
    if _token_expirado(registro, instante_atual):
        del _tokens[token_hash]
        raise HTTPException(status_code=410, detail="Token expirado.")

    definir_senha(registro.usuario_id, payload.nova_senha)
    registro.usado = True
    del _tokens[token_hash]

    return {"mensagem": "Senha redefinida com sucesso."}