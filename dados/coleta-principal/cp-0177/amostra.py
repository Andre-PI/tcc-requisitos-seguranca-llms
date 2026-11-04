from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
import hashlib
import hmac
import secrets
import threading
from typing import Dict, Any

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKEN_BYTES = 32
_VALIDADE_SEGUNDOS = 900.0
_lock = threading.Lock()
_tokens: Dict[str, Dict[str, Any]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _limpar_expirados() -> None:
    atual = agora()
    expirados = [h for h, dados in _tokens.items() if atual >= dados["expira_em"]]
    for h in expirados:
        _tokens.pop(h, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)

    if usuario is not None:
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        resumo = _hash_token(token)
        with _lock:
            _limpar_expirados()
            _tokens[resumo] = {
                "usuario_id": usuario["id"],
                "expira_em": agora() + _VALIDADE_SEGUNDOS,
                "usado": False,
            }
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail existir, um token de recuperação foi enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    resumo = _hash_token(payload.token)

    with _lock:
        _limpar_expirados()
        dados = _tokens.get(resumo)

        if dados is None:
            raise HTTPException(status_code=404, detail="Token inválido.")

        if dados["usado"]:
            raise HTTPException(status_code=410, detail="Token já utilizado.")

        if agora() >= dados["expira_em"]:
            _tokens.pop(resumo, None)
            raise HTTPException(status_code=410, detail="Token expirado.")

        usuario_id = dados["usuario_id"]
        dados["usado"] = True
        _tokens.pop(resumo, None)

    definir_senha(usuario_id, payload.nova_senha)
    return {"mensagem": "Senha redefinida com sucesso."}