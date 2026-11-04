import hashlib
import secrets
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_VALIDITY_SECONDS = 900.0  # 15 minutos

# Armazena tokens em memória: token_hash -> {"usuario_id": int, "expira_em": float}
_tokens_recuperacao: Dict[str, Dict[str, Any]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, max_length=128)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _limpar_tokens_expirados(tempo_atual: float) -> None:
    tokens_para_remover = [
        t_hash for t_hash, dados in _tokens_recuperacao.items()
        if dados["expira_em"] <= tempo_atual
    ]
    for t_hash in tokens_para_remover:
        _tokens_recuperacao.pop(t_hash, None)


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest) -> Dict[str, str]:
    tempo_atual = agora()
    _limpar_tokens_expirados(tempo_atual)

    usuario = usuario_por_email(dados.email)
    if usuario:
        # Invalida tokens anteriores do mesmo usuário
        tokens_anteriores = [
            t_hash for t_hash, info in _tokens_recuperacao.items()
            if info["usuario_id"] == usuario["id"]
        ]
        for t_hash in tokens_anteriores:
            _tokens_recuperacao.pop(t_hash, None)

        token_plano = secrets.token_urlsafe(32)
        token_hash = _hash_token(token_plano)
        _tokens_recuperacao[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": tempo_atual + TOKEN_VALIDITY_SECONDS,
        }
        enviar_email(usuario["email"], token_plano)

    # Resposta genérica para mitigar User Enumeration (OWASP)
    return {"mensagem": "Se o e-mail estiver cadastrado, as instruções de recuperação foram enviadas."}


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest) -> Dict[str, str]:
    tempo_atual = agora()
    _limpar_tokens_expirados(tempo_atual)

    token_hash = _hash_token(dados.token)
    info_token = _tokens_recuperacao.pop(token_hash, None)

    if not info_token or info_token["expira_em"] <= tempo_atual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado."
        )

    definir_senha(info_token["usuario_id"], dados.nova_senha)

    return {"mensagem": "Senha redefinida com sucesso."}