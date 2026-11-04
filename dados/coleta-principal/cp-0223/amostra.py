from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
import hashlib
import secrets
import time
from typing import Dict, Tuple

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKEN_BYTES = 32
_TOKEN_TTL_SECONDS = 900.0

# token_hash -> (usuario_id, expira_em, usado)
_tokens: Dict[str, Tuple[int, float, bool]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados() -> None:
    atual = agora()
    expirados = [h for h, (_, expira_em, usado) in _tokens.items() if usado or expira_em <= atual]
    for h in expirados:
        _tokens.pop(h, None)


def _gerar_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(req.email)
    if usuario is not None:
        token = _gerar_token()
        token_hash = _hash_token(token)
        _tokens[token_hash] = (usuario["id"], agora() + _TOKEN_TTL_SECONDS, False)
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha."}


@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    token_hash = _hash_token(req.token)
    registro = _tokens.get(token_hash)

    if registro is None:
        raise HTTPException(status_code=404, detail="Token inválido.")
    
    usuario_id, expira_em, usado = registro
    if usado:
        raise HTTPException(status_code=410, detail="Token já utilizado.")
    if agora() >= expira_em:
        _tokens.pop(token_hash, None)
        raise HTTPException(status_code=410, detail="Token expirado.")

    definir_senha(usuario_id, req.nova_senha)
    _tokens[token_hash] = (usuario_id, expira_em, True)

    return {"mensagem": "Senha redefinida com sucesso."}