from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from threading import Lock
import secrets
from typing import Dict, Tuple

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKEN_TTL_SECONDS = 3600.0
_tokens: Dict[str, Tuple[int, float]] = {}
_lock = Lock()


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados() -> None:
    atual = agora()
    expirados = [token for token, (_, expira_em) in _tokens.items() if expira_em <= atual]
    for token in expirados:
        _tokens.pop(token, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = secrets.token_urlsafe(32)
    expira_em = agora() + _TOKEN_TTL_SECONDS

    with _lock:
        _limpar_tokens_expirados()
        _tokens[token] = (usuario["id"], expira_em)

    enviar_email(usuario["email"], token)
    return {"mensagem": "Token de recuperação enviado por e-mail"}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    with _lock:
        _limpar_tokens_expirados()
        dados = _tokens.pop(payload.token, None)

    if dados is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    usuario_id, _ = dados
    definir_senha(usuario_id, payload.nova_senha)
    return {"mensagem": "Senha redefinida com sucesso"}