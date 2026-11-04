from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Tuple
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_token_store: Dict[str, Tuple[int, float]] = {}
TOKEN_TTL_SEGUNDOS = 3600.0


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = secrets.token_urlsafe(32)
    _token_store[token] = (usuario["id"], agora())
    enviar_email(usuario["email"], token)

    return {"mensagem": "Token de recuperação enviado com sucesso"}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    dados = _token_store.get(payload.token)
    if dados is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    usuario_id, criado_em = dados
    if agora() - criado_em > TOKEN_TTL_SEGUNDOS:
        _token_store.pop(payload.token, None)
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    definir_senha(usuario_id, payload.nova_senha)
    _token_store.pop(payload.token, None)

    return {"mensagem": "Senha redefinida com sucesso"}