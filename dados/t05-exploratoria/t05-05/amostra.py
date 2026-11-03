from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Any
import secrets
from threading import Lock

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_token_lock = Lock()
_tokens: Dict[str, Dict[str, Any]] = {}
_TOKEN_TTL_SECONDS = 900.0


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados() -> None:
    atual = agora()
    expirados = [
        token
        for token, dados in _tokens.items()
        if atual - float(dados["criado_em"]) > _TOKEN_TTL_SECONDS
    ]
    for token in expirados:
        _tokens.pop(token, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = secrets.token_urlsafe(32)
    with _token_lock:
        _limpar_tokens_expirados()
        _tokens[token] = {
            "usuario_id": usuario["id"],
            "email": usuario["email"],
            "criado_em": agora(),
        }

    enviar_email(usuario["email"], token)
    return {"mensagem": "Token de recuperação enviado por e-mail"}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    with _token_lock:
        _limpar_tokens_expirados()
        dados = _tokens.get(payload.token)
        if dados is None:
            raise HTTPException(status_code=400, detail="Token inválido ou expirado")
        usuario_id = int(dados["usuario_id"])
        _tokens.pop(payload.token, None)

    definir_senha(usuario_id, payload.nova_senha)
    return {"mensagem": "Senha redefinida com sucesso"}