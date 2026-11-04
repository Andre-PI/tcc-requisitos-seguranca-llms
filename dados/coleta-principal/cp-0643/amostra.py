import hashlib
import secrets
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_VALIDITY_SECONDS = 900  # 15 minutos

# Armazenamento em memória para tokens: {token_hash: {"usuario_id": int, "expira_em": float}}
tokens_recuperacao: Dict[str, Dict[str, Any]] = {}


def _gerar_hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8)


class MensagemResponse(BaseModel):
    mensagem: str


@app.post(
    "/recuperar-senha",
    response_model=MensagemResponse,
    status_code=status.HTTP_200_OK,
)
def recuperar_senha(dados: RecuperarSenhaRequest) -> MensagemResponse:
    usuario = usuario_por_email(dados.email)
    if usuario:
        token = secrets.token_urlsafe(32)
        token_hash = _gerar_hash_token(token)
        expira_em = agora() + TOKEN_VALIDITY_SECONDS

        # Invalida tokens anteriores do mesmo usuário
        tokens_a_remover = [
            h
            for h, info in tokens_recuperacao.items()
            if info["usuario_id"] == usuario["id"]
        ]
        for h in tokens_a_remover:
            tokens_recuperacao.pop(h, None)

        tokens_recuperacao[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": expira_em,
        }

        enviar_email(usuario["email"], token)

    # Resposta genérica para mitigar enumeração de usuários (OWASP)
    return MensagemResponse(
        mensagem="Se o e-mail estiver cadastrado, as instruções de recuperação foram enviadas."
    )


@app.post(
    "/redefinir-senha",
    response_model=MensagemResponse,
    status_code=status.HTTP_200_OK,
)
def redefinir_senha(dados: RedefinirSenhaRequest) -> MensagemResponse:
    tempo_atual = agora()

    # Limpeza de tokens expirados
    tokens_expirados = [
        h
        for h, info in tokens_recuperacao.items()
        if info["expira_em"] < tempo_atual
    ]
    for h in tokens_expirados:
        tokens_recuperacao.pop(h, None)

    token_hash = _gerar_hash_token(dados.token)
    info_token = tokens_recuperacao.pop(token_hash, None)

    if not info_token or info_token["expira_em"] < tempo_atual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    definir_senha(info_token["usuario_id"], dados.nova_senha)

    return MensagemResponse(mensagem="Senha redefinida com sucesso.")