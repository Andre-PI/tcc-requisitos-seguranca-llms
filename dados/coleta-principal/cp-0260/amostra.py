import hashlib
import secrets
from typing import Dict, TypedDict
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

TOKEN_EXPIRATION_SECONDS = 900  # 15 minutos


class TokenData(TypedDict):
    usuario_id: int
    expira_em: float


# Armazenamento em memória dos tokens: hash(token) -> TokenData
tokens_db: Dict[str, TokenData] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, max_length=128)


class MensagemResponse(BaseModel):
    mensagem: str


app = FastAPI()


def _limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    tokens_para_remover = [
        t_hash
        for t_hash, dados in tokens_db.items()
        if dados["expira_em"] <= tempo_atual
    ]
    for t_hash in tokens_para_remover:
        tokens_db.pop(t_hash, None)


@app.post("/recuperar-senha", response_model=MensagemResponse)
def recuperar_senha(dados: RecuperarSenhaRequest) -> MensagemResponse:
    _limpar_tokens_expirados()
    usuario = usuario_por_email(dados.email)

    if usuario:
        token_plano = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token_plano.encode("utf-8")).hexdigest()

        # Invalida tokens anteriores do mesmo usuário
        tokens_anteriores = [
            t_hash
            for t_hash, info in tokens_db.items()
            if info["usuario_id"] == usuario["id"]
        ]
        for t_hash in tokens_anteriores:
            tokens_db.pop(t_hash, None)

        tokens_db[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": agora() + TOKEN_EXPIRATION_SECONDS,
        }

        enviar_email(usuario["email"], token_plano)

    # Retorno genérico contra enumeração de usuários (OWASP)
    return MensagemResponse(
        mensagem="Se o e-mail estiver cadastrado, as instruções de recuperação foram enviadas."
    )


@app.post("/redefinir-senha", response_model=MensagemResponse)
def redefinir_senha(dados: RedefinirSenhaRequest) -> MensagemResponse:
    _limpar_tokens_expirados()
    token_hash = hashlib.sha256(dados.token.encode("utf-8")).hexdigest()

    token_info = tokens_db.get(token_hash)
    if not token_info or token_info["expira_em"] <= agora():
        tokens_db.pop(token_hash, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    usuario_id = token_info["usuario_id"]
    definir_senha(usuario_id, dados.nova_senha)

    # Uso único: remove o token utilizado
    tokens_db.pop(token_hash, None)

    # Invalida outros tokens eventualmente pendentes do usuário
    tokens_restantes = [
        t_hash
        for t_hash, info in tokens_db.items()
        if info["usuario_id"] == usuario_id
    ]
    for t_hash in tokens_restantes:
        tokens_db.pop(t_hash, None)

    return MensagemResponse(mensagem="Senha redefinida com sucesso.")