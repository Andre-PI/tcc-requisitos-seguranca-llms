from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from secrets import token_urlsafe
from typing import Dict, Tuple

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_EXPIRACAO_SEGUNDOS = 3600
_tokens: Dict[str, Tuple[int, float]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = token_urlsafe(32)
    _tokens[token] = (usuario["id"], agora())
    enviar_email(usuario["email"], token)

    return {"mensagem": "Token de recuperação enviado com sucesso"}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    dados_token = _tokens.get(payload.token)
    if dados_token is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    usuario_id, criado_em = dados_token
    if agora() - criado_em > TOKEN_EXPIRACAO_SEGUNDOS:
        _tokens.pop(payload.token, None)
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    definir_senha(usuario_id, payload.nova_senha)
    _tokens.pop(payload.token, None)

    return {"mensagem": "Senha redefinida com sucesso"}