import hashlib
import secrets
from typing import Dict, TypedDict
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

TOKEN_EXPIRACAO_SEGUNDOS = 900  # 15 minutos


class TokenData(TypedDict):
    usuario_id: int
    expiracao: float


# Armazenamento em memória: hash_do_token -> TokenData
tokens_db: Dict[str, TokenData] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, max_length=128)


class RespostaPadrao(BaseModel):
    mensagem: str


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def limpar_tokens_expirados(tempo_atual: float) -> None:
    tokens_para_remover = [
        t_hash
        for t_hash, dados in tokens_db.items()
        if tempo_atual > dados["expiracao"]
    ]
    for t_hash in tokens_para_remover:
        tokens_db.pop(t_hash, None)


app = FastAPI()


@app.post(
    "/recuperar-senha",
    response_model=RespostaPadrao,
    status_code=status.HTTP_200_OK,
)
def recuperar_senha(requisicao: RecuperarSenhaRequest) -> RespostaPadrao:
    tempo_atual = agora()
    limpar_tokens_expirados(tempo_atual)

    usuario = usuario_por_email(requisicao.email)

    if usuario:
        # Invalidar tokens anteriores do mesmo usuário
        tokens_antigos = [
            t_hash
            for t_hash, dados in tokens_db.items()
            if dados["usuario_id"] == usuario["id"]
        ]
        for t_hash in tokens_antigos:
            tokens_db.pop(t_hash, None)

        token = secrets.token_urlsafe(32)
        token_hashed = hash_token(token)

        tokens_db[token_hashed] = {
            "usuario_id": usuario["id"],
            "expiracao": tempo_atual + TOKEN_EXPIRACAO_SEGUNDOS,
        }

        enviar_email(usuario["email"], token)

    # Mensagem genérica para mitigar enumeração de contas (OWASP)
    return RespostaPadrao(
        mensagem="Se o e-mail estiver cadastrado, as instruções para redefinição foram enviadas."
    )


@app.post(
    "/redefinir-senha",
    response_model=RespostaPadrao,
    status_code=status.HTTP_200_OK,
)
def redefinir_senha(requisicao: RedefinirSenhaRequest) -> RespostaPadrao:
    tempo_atual = agora()
    limpar_tokens_expirados(tempo_atual)

    token_hashed = hash_token(requisicao.token)
    dados_token = tokens_db.get(token_hashed)

    if not dados_token or tempo_atual > dados_token["expiracao"]:
        tokens_db.pop(token_hashed, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    definir_senha(dados_token["usuario_id"], requisicao.nova_senha)

    # Invalida o token após uso único
    tokens_db.pop(token_hashed, None)

    return RespostaPadrao(mensagem="Senha redefinida com sucesso.")