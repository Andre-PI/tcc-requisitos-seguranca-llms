from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
import hashlib
import secrets
from threading import Lock

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKEN_VALIDITY_SECONDS = 900.0
_TOKEN_BYTES = 32

_lock = Lock()
_tokens = {}  # token_hash_hex -> {"usuario_id": int, "expira_em": float, "usado": bool}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _gerar_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


@app.post("/recuperar-senha", status_code=200)
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)
    if usuario is not None:
        token = _gerar_token()
        token_hash = _hash_token(token)
        expira_em = float(agora()) + _TOKEN_VALIDITY_SECONDS
        with _lock:
            _tokens[token_hash] = {
                "usuario_id": usuario["id"],
                "expira_em": expira_em,
                "usado": False,
            }
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha."}


@app.post("/redefinir-senha", status_code=200)
def redefinir_senha(payload: RedefinirSenhaRequest):
    token_hash = _hash_token(payload.token)
    now = float(agora())

    with _lock:
        registro = _tokens.get(token_hash)
        if registro is None:
            raise HTTPException(status_code=404, detail="Token inválido.")
        if registro["usado"]:
            raise HTTPException(status_code=410, detail="Token já utilizado.")
        if now >= registro["expira_em"]:
            del _tokens[token_hash]
            raise HTTPException(status_code=410, detail="Token expirado.")
        usuario_id = registro["usuario_id"]
        registro["usado"] = True
        del _tokens[token_hash]

    definir_senha(usuario_id, payload.nova_senha)
    return {"mensagem": "Senha redefinida com sucesso."}