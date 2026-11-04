from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Any
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

# Token storage in memory:
# token -> {"usuario_id": int, "email": str, "expira_em": float}
_tokens: Dict[str, Dict[str, Any]] = {}

# Token validity window in seconds
_TOKEN_TTL = 3600.0


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados() -> None:
    atual = agora()
    expirados = [token for token, dados in _tokens.items() if dados["expira_em"] <= atual]
    for token in expirados:
        _tokens.pop(token, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    token = secrets.token_urlsafe(32)
    _tokens[token] = {
        "usuario_id": usuario["id"],
        "email": usuario["email"],
        "expira_em": agora() + _TOKEN_TTL,
    }

    enviar_email(usuario["email"], token)

    return {"mensagem": "Token de recuperacao enviado com sucesso."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    dados = _tokens.get(payload.token)
    if dados is None:
        raise HTTPException(status_code=400, detail="Token invalido ou expirado")

    definir_senha(dados["usuario_id"], payload.nova_senha)
    _tokens.pop(payload.token, None)

    return {"mensagem": "Senha redefinida com sucesso."}