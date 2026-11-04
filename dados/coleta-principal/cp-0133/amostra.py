from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Any
from uuid import uuid4

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKEN_TTL_SEGUNDOS = 3600.0
_tokens: Dict[str, Dict[str, Any]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    expirados = [
        token
        for token, dados in _tokens.items()
        if tempo_atual - float(dados["criado_em"]) > _TOKEN_TTL_SEGUNDOS
    ]
    for token in expirados:
        del _tokens[token]


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    token = uuid4().hex
    _tokens[token] = {
        "usuario_id": usuario["id"],
        "email": usuario["email"],
        "criado_em": agora(),
    }

    enviar_email(usuario["email"], token)
    return {"mensagem": "Token de recuperação enviado com sucesso."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    dados = _tokens.get(payload.token)
    if dados is None:
        raise HTTPException(status_code=400, detail="Token invalido ou expirado")

    definir_senha(dados["usuario_id"], payload.nova_senha)
    del _tokens[payload.token]

    return {"mensagem": "Senha redefinida com sucesso."}