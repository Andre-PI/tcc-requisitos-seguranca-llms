from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_EXPIRACAO_SEGUNDOS = 3600
_tokens: Dict[str, dict] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(str(payload.email))
    if usuario is not None:
        token = secrets.token_urlsafe(32)
        _tokens[token] = {
            "usuario_id": usuario["id"],
            "email": usuario["email"],
            "expira_em": agora() + TOKEN_EXPIRACAO_SEGUNDOS,
        }
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação foi enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    dados = _tokens.get(payload.token)
    if dados is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    if agora() > dados["expira_em"]:
        _tokens.pop(payload.token, None)
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    definir_senha(dados["usuario_id"], payload.nova_senha)
    _tokens.pop(payload.token, None)

    return {"mensagem": "Senha redefinida com sucesso."}