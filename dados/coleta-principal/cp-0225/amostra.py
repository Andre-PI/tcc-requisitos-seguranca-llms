from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
import hashlib
import secrets
import threading
from typing import Dict, Optional

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKEN_VALIDADE_SEGUNDOS = 900
_TOKEN_BYTES = 32

_lock = threading.Lock()
_tokens: Dict[str, dict] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _agora() -> float:
    return float(agora())


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _gerar_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    usuario = usuario_por_email(payload.email)

    if usuario is not None:
        token = _gerar_token()
        token_hash = _hash_token(token)
        expira_em = _agora() + _TOKEN_VALIDADE_SEGUNDOS

        with _lock:
            _tokens[token_hash] = {
                "usuario_id": usuario["id"],
                "expira_em": expira_em,
                "usado": False,
            }

        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação foi enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    token_hash = _hash_token(payload.token)

    with _lock:
        registro = _tokens.get(token_hash)

        if registro is None:
            raise HTTPException(status_code=404, detail="Token inválido.")

        if registro["usado"]:
            raise HTTPException(status_code=410, detail="Token já utilizado.")

        if _agora() >= registro["expira_em"]:
            del _tokens[token_hash]
            raise HTTPException(status_code=410, detail="Token expirado.")

        usuario_id = registro["usuario_id"]
        definir_senha(usuario_id, payload.nova_senha)
        registro["usado"] = True
        del _tokens[token_hash]

    return {"mensagem": "Senha redefinida com sucesso."}