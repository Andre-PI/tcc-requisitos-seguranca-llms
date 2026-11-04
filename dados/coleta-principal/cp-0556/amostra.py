from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Tuple
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKENS: Dict[str, Tuple[int, float]] = {}
_TOKEN_TTL_SECONDS = 15 * 60


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)

    if usuario is None:
        return {"mensagem": "Se o e-mail estiver cadastrado, você receberá um token de recuperação."}

    token = secrets.token_urlsafe(32)
    _TOKENS[token] = (usuario["id"], agora() + _TOKEN_TTL_SECONDS)
    enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá um token de recuperação."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    registro = _TOKENS.get(payload.token)

    if registro is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    usuario_id, expira_em = registro
    if agora() > expira_em:
        _TOKENS.pop(payload.token, None)
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    definir_senha(usuario_id, payload.nova_senha)
    _TOKENS.pop(payload.token, None)

    return {"mensagem": "Senha redefinida com sucesso."}