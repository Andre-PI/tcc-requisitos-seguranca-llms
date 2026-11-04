from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Tuple
import secrets
from time import time

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_token_store: Dict[str, Tuple[int, float]] = {}
_TOKEN_TTL_SECONDS = 3600.0


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados() -> None:
    atual = agora()
    expirados = [token for token, (_, expira_em) in _token_store.items() if expira_em <= atual]
    for token in expirados:
        _token_store.pop(token, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = secrets.token_urlsafe(32)
    _token_store[token] = (usuario["id"], agora() + _TOKEN_TTL_SECONDS)
    enviar_email(usuario["email"], token)

    return {"mensagem": "Token de recuperação enviado com sucesso."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    dados = _token_store.pop(payload.token, None)
    if dados is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    usuario_id, _ = dados
    definir_senha(usuario_id, payload.nova_senha)

    return {"mensagem": "Senha redefinida com sucesso."}