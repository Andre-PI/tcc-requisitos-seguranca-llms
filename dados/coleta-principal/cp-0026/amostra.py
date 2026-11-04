from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from secrets import token_urlsafe, compare_digest
from threading import Lock
from typing import Dict, Tuple

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_TTL_SEGUNDOS = 3600
TOKEN_BYTES = 32

_tokens: Dict[str, Tuple[int, float]] = {}
_lock = Lock()


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=8, max_length=256)


def _limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    expirados = [t for t, (_, expira_em) in _tokens.items() if expira_em <= tempo_atual]
    for t in expirados:
        _tokens.pop(t, None)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)

    if usuario is None:
        return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação foi enviado."}

    token = token_urlsafe(TOKEN_BYTES)
    expira_em = agora() + TOKEN_TTL_SEGUNDOS

    with _lock:
        _limpar_tokens_expirados()
        _tokens[token] = (usuario["id"], expira_em)

    enviar_email(usuario["email"], token)
    return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação foi enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    usuario_id = None
    token_recebido = payload.token

    with _lock:
        _limpar_tokens_expirados()
        for token_salvo, (uid, expira_em) in list(_tokens.items()):
            if compare_digest(token_salvo, token_recebido):
                usuario_id = uid
                if expira_em <= agora():
                    _tokens.pop(token_salvo, None)
                    usuario_id = None
                else:
                    _tokens.pop(token_salvo, None)
                break

    if usuario_id is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    definir_senha(usuario_id, payload.nova_senha)
    return {"mensagem": "Senha redefinida com sucesso."}