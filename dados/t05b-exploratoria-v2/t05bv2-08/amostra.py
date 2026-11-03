from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_EXPIRACAO_SEGUNDOS = 3600
_tokens: Dict[str, Dict[str, float | int]] = {}


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
    _tokens[token] = {
        "usuario_id": usuario["id"],
        "expira_em": agora() + TOKEN_EXPIRACAO_SEGUNDOS,
    }

    enviar_email(usuario["email"], token)

    return {"mensagem": "Token de recuperação enviado com sucesso"}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    dados_token = _tokens.get(payload.token)
    if dados_token is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    if agora() > float(dados_token["expira_em"]):
        del _tokens[payload.token]
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    definir_senha(int(dados_token["usuario_id"]), payload.nova_senha)
    del _tokens[payload.token]

    return {"mensagem": "Senha redefinida com sucesso"}