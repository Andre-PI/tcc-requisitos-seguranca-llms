from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Tuple
import secrets
import hmac

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_TTL_SECONDS = 3600
MAX_TOKENS_POR_EMAIL = 5
MAX_TOKENS_TOTAL = 10000

_tokens_por_codigo: Dict[str, Tuple[int, str, float]] = {}
_tokens_por_email: Dict[str, set[str]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    nova_senha: str = Field(min_length=8, max_length=256)


def _limpar_tokens_expirados() -> None:
    atual = agora()
    expirados = [token for token, (_, _, expira_em) in _tokens_por_codigo.items() if expira_em <= atual]
    for token in expirados:
        _, email, _ = _tokens_por_codigo.pop(token, (None, None, None))
        if email is not None and email in _tokens_por_email:
            _tokens_por_email[email].discard(token)
            if not _tokens_por_email[email]:
                _tokens_por_email.pop(email, None)


def _gerar_token() -> str:
    return secrets.token_urlsafe(32)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(payload.email)
    if usuario is None:
        return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação será enviado."}

    email = usuario["email"]
    usuario_id = usuario["id"]

    tokens_do_email = _tokens_por_email.setdefault(email, set())
    while len(tokens_do_email) >= MAX_TOKENS_POR_EMAIL:
        token_antigo = next(iter(tokens_do_email))
        tokens_do_email.remove(token_antigo)
        _tokens_por_codigo.pop(token_antigo, None)

    if len(_tokens_por_codigo) >= MAX_TOKENS_TOTAL:
        _limpar_tokens_expirados()
        if len(_tokens_por_codigo) >= MAX_TOKENS_TOTAL:
            raise HTTPException(status_code=503, detail="Serviço temporariamente indisponível.")

    token = _gerar_token()
    expira_em = agora() + TOKEN_TTL_SECONDS
    _tokens_por_codigo[token] = (usuario_id, email, expira_em)
    tokens_do_email.add(token)

    enviar_email(email, token)
    return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação será enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    dados = _tokens_por_codigo.get(payload.token)
    if dados is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    usuario_id, email, expira_em = dados
    if expira_em <= agora():
        _tokens_por_codigo.pop(payload.token, None)
        if email in _tokens_por_email:
            _tokens_por_email[email].discard(payload.token)
            if not _tokens_por_email[email]:
                _tokens_por_email.pop(email, None)
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    definir_senha(usuario_id, payload.nova_senha)

    _tokens_por_codigo.pop(payload.token, None)
    if email in _tokens_por_email:
        _tokens_por_email[email].discard(payload.token)
        if not _tokens_por_email[email]:
            _tokens_por_email.pop(email, None)

    return {"mensagem": "Senha redefinida com sucesso."}