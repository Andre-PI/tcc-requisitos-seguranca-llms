from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Tuple
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKEN_TTL_SECONDS = 3600.0
_tokens: Dict[str, Tuple[int, float]] = {}


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
    _tokens[token] = (usuario["id"], float(agora()))
    enviar_email(usuario["email"], token)
    return {"mensagem": "Token de recuperação enviado por e-mail"}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    registro = _tokens.get(payload.token)
    if registro is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    usuario_id, criado_em = registro
    if float(agora()) - criado_em > _TOKEN_TTL_SECONDS:
        _tokens.pop(payload.token, None)
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    definir_senha(usuario_id, payload.nova_senha)
    _tokens.pop(payload.token, None)
    return {"mensagem": "Senha redefinida com sucesso"}