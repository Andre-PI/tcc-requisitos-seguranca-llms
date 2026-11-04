from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Tuple
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKEN_TTL_SEGUNDOS = 3600.0
_tokens: Dict[str, Tuple[int, float]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    expirados = [token for token, (_, criado_em) in _tokens.items() if tempo_atual - criado_em > _TOKEN_TTL_SEGUNDOS]
    for token in expirados:
        _tokens.pop(token, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    _limpar_tokens_expirados()
    token = secrets.token_urlsafe(32)
    _tokens[token] = (usuario["id"], agora())
    enviar_email(usuario["email"], token)

    return {"mensagem": "Token de recuperação enviado com sucesso."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()
    dados_token = _tokens.get(payload.token)
    if dados_token is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    usuario_id, criado_em = dados_token
    if agora() - criado_em > _TOKEN_TTL_SEGUNDOS:
        _tokens.pop(payload.token, None)
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    definir_senha(usuario_id, payload.nova_senha)
    _tokens.pop(payload.token, None)

    return {"mensagem": "Senha redefinida com sucesso."}