import hashlib
import secrets
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from tcc_t05_infra import (
    usuario_por_email,
    definir_senha,
    enviar_email,
    agora,
)

app = FastAPI()

TOKEN_EXPIRACAO_SEGUNDOS = 900  # 15 minutos

# Armazena os tokens na memória: token_hash -> {"usuario_id": int, "expiracao": float, "usado": bool}
tokens_db: Dict[str, Dict[str, Any]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, max_length=128)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest):
    usuario = usuario_por_email(dados.email)
    if usuario:
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        tempo_atual = agora()
        tokens_db[token_hash] = {
            "usuario_id": usuario["id"],
            "expiracao": tempo_atual + TOKEN_EXPIRACAO_SEGUNDOS,
            "usado": False,
        }
        enviar_email(usuario["email"], token)

    # Resposta genérica para evitar enumeração de usuários (OWASP)
    return {
        "mensagem": "Se o e-mail informado estiver cadastrado, as instruções para redefinição de senha foram enviadas."
    }


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest):
    token_hash = _hash_token(dados.token)
    registro = tokens_db.get(token_hash)
    tempo_atual = agora()

    if not registro or registro["usado"] or tempo_atual > registro["expiracao"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    # Invalidação imediata do token para evitar reutilização
    registro["usado"] = True
    definir_senha(registro["usuario_id"], dados.nova_senha)

    return {"mensagem": "Senha redefinida com sucesso."}