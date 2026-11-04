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

TOKEN_VALIDITY_SECONDS = 900  # 15 minutos


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, max_length=128)


class MensagemResponse(BaseModel):
    mensagem: str


# Armazenamento em memória dos tokens: token_hash -> {"usuario_id": int, "expira_em": float}
_tokens_db: Dict[str, Dict[str, Any]] = {}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.post("/recuperar-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest):
    email_normalizado = dados.email.strip().lower()
    usuario = usuario_por_email(email_normalizado)

    if usuario:
        usuario_id = usuario["id"]

        # Invalida tokens anteriores do mesmo usuário
        tokens_para_remover = [
            th for th, info in _tokens_db.items() if info["usuario_id"] == usuario_id
        ]
        for th in tokens_para_remover:
            del _tokens_db[th]

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expira_em = agora() + TOKEN_VALIDITY_SECONDS

        _tokens_db[token_hash] = {
            "usuario_id": usuario_id,
            "expira_em": expira_em,
        }

        enviar_email(usuario["email"], raw_token)

    # Resposta genérica para evitar enumeração de usuários (OWASP)
    return {"mensagem": "Se o e-mail informado estiver cadastrado, as instruções foram enviadas."}


@app.post("/redefinir-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest):
    token_hash = _hash_token(dados.token)
    registro = _tokens_db.get(token_hash)
    tempo_atual = agora()

    if not registro or tempo_atual > registro["expira_em"]:
        if registro:
            del _tokens_db[token_hash]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    usuario_id = registro["usuario_id"]
    definir_senha(usuario_id, dados.nova_senha)

    # Invalida o token após uso único
    del _tokens_db[token_hash]

    return {"mensagem": "Senha redefinida com sucesso."}