import hashlib
import secrets
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_VALIDADE_SEGUNDOS = 900  # 15 minutos

# Armazenamento em memória dos tokens: hash(token) -> {"usuario_id": int, "expira_em": float}
tokens_ativos: Dict[str, Dict[str, Any]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, max_length=128)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _limpar_tokens_expirados(tempo_atual: float) -> None:
    tokens_para_remover = [
        t_hash
        for t_hash, dados in tokens_ativos.items()
        if dados["expira_em"] <= tempo_atual
    ]
    for t_hash in tokens_para_remover:
        del tokens_ativos[t_hash]


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest) -> Dict[str, str]:
    tempo_atual = agora()
    _limpar_tokens_expirados(tempo_atual)

    usuario = usuario_por_email(dados.email)
    if usuario is not None:
        token_plano = secrets.token_urlsafe(32)
        token_hash = _hash_token(token_plano)

        # Invalida tokens anteriores do mesmo usuário
        tokens_anteriores = [
            t_hash
            for t_hash, info in tokens_ativos.items()
            if info["usuario_id"] == usuario["id"]
        ]
        for t_hash in tokens_anteriores:
            del tokens_ativos[t_hash]

        tokens_ativos[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": tempo_atual + TOKEN_VALIDADE_SEGUNDOS,
        }

        enviar_email(usuario["email"], token_plano)

    # Resposta genérica para mitigar enumeração de usuários (OWASP)
    return {
        "mensagem": "Se o e-mail estiver cadastrado, as instruções de recuperação serão enviadas."
    }


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest) -> Dict[str, str]:
    tempo_atual = agora()
    _limpar_tokens_expirados(tempo_atual)

    token_hash = _hash_token(dados.token)
    registro = tokens_ativos.get(token_hash)

    if not registro or registro["expira_em"] <= tempo_atual:
        if token_hash in tokens_ativos:
            del tokens_ativos[token_hash]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    # Invalidação imediata do token para evitar reuso (OWASP)
    del tokens_ativos[token_hash]

    definir_senha(registro["usuario_id"], dados.nova_senha)

    return {"mensagem": "Senha redefinida com sucesso."}