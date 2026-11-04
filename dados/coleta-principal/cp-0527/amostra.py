from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Tuple
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_TTL_SEGUNDOS = 3600.0
_tokens: Dict[str, Tuple[int, float]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    expirados = [token for token, (_, expira_em) in _tokens.items() if expira_em <= tempo_atual]
    for token in expirados:
        _tokens.pop(token, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(str(payload.email))
    if usuario is None:
        return {"mensagem": "Se o e-mail existir, um token de recuperação foi enviado."}

    token = secrets.token_urlsafe(32)
    _tokens[token] = (int(usuario["id"]), agora() + TOKEN_TTL_SEGUNDOS)
    enviar_email(str(payload.email), token)

    return {"mensagem": "Se o e-mail existir, um token de recuperação foi enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    dados = _tokens.pop(payload.token, None)
    if dados is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    usuario_id, _ = dados
    definir_senha(usuario_id, payload.nova_senha)

    return {"mensagem": "Senha redefinida com sucesso."}