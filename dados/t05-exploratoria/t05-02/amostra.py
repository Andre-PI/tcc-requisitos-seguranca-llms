from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora
import secrets
import threading

app = FastAPI()

# Token storage: token -> {usuario_id, exp}
# Protegido por lock para concorrência
_tokens = {}
_tokens_lock = threading.Lock()

TOKEN_EXPIRATION_SECONDS = 3600  # 1 hora


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr
    class Config:
        extra = "ignore"


class RedefinirSenhaRequest(BaseModel):
    token: constr(min_length=32, max_length=128)
    nova_senha: constr(min_length=8)
    class Config:
        extra = "ignore"


def _limpar_tokens_expirados():
    agora_ts = agora()
    with _tokens_lock:
        expired = [t for t, v in _tokens.items() if v["exp"] <= agora_ts]
        for t in expired:
            del _tokens[t]


@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(req.email)
    if usuario:
        token = secrets.token_urlsafe(48)
        exp = agora() + TOKEN_EXPIRATION_SECONDS
        with _tokens_lock:
            _tokens[token] = {"usuario_id": usuario["id"], "exp": exp}
        enviar_email(usuario["email"], token)
    # Resposta genérica para evitar enumeração de usuários
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."},
    )


@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    _limpar_tokens_expirados()
    with _tokens_lock:
        token_data = _tokens.get(req.token)
        if not token_data:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"mensagem": "Token inválido ou expirado."},
            )
        usuario_id = token_data["usuario_id"]
        del _tokens[req.token]

    definir_senha(usuario_id, req.nova_senha)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"mensagem": "Senha redefinida com sucesso."},
    )