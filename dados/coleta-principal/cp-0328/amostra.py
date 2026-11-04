from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKENS: Dict[str, dict] = {}
_TTL_SEGUNDOS = 3600


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    token = secrets.token_urlsafe(32)
    _TOKENS[token] = {
        "usuario_id": usuario["id"],
        "email": usuario["email"],
        "expira_em": agora() + _TTL_SEGUNDOS,
    }

    enviar_email(usuario["email"], token)
    return {"mensagem": "Token de recuperacao enviado com sucesso."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    dados = _TOKENS.get(payload.token)
    if not dados:
        raise HTTPException(status_code=400, detail="Token invalido ou expirado")

    if agora() > dados["expira_em"]:
        _TOKENS.pop(payload.token, None)
        raise HTTPException(status_code=400, detail="Token invalido ou expirado")

    definir_senha(dados["usuario_id"], payload.nova_senha)
    _TOKENS.pop(payload.token, None)
    return {"mensagem": "Senha redefinida com sucesso."}