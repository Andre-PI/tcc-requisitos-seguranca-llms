from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_EXPIRACAO_SEGUNDOS = 15 * 60  # 15 minutos
tokens_por_email: Dict[str, Dict[str, float | int]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    email: EmailStr
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = f"{secrets.randbelow(10**6):06d}"
    tokens_por_email[payload.email] = {
        "token": token,
        "usuario_id": usuario["id"],
        "expira_em": agora() + TOKEN_EXPIRACAO_SEGUNDOS,
    }

    enviar_email(payload.email, token)
    return {"mensagem": "Token de recuperação enviado por e-mail"}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    dados_token = tokens_por_email.get(payload.email)
    if dados_token is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    if agora() > float(dados_token["expira_em"]):
        tokens_por_email.pop(payload.email, None)
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    if payload.token != dados_token["token"]:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    definir_senha(int(dados_token["usuario_id"]), payload.nova_senha)
    tokens_por_email.pop(payload.email, None)
    return {"mensagem": "Senha redefinida com sucesso"}