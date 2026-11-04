import hashlib
import secrets
from typing import Dict, TypedDict
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

TOKEN_EXPIRACAO_SEGUNDOS = 900  # 15 minutos


class TokenData(TypedDict):
    usuario_id: int
    expira_em: float


# Armazena hash_sha256(token) -> TokenData
tokens_db: Dict[str, TokenData] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, max_length=128)


class MensagemResponse(BaseModel):
    mensagem: str


def limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    expirados = [h for h, data in tokens_db.items() if data["expira_em"] <= tempo_atual]
    for h in expirados:
        tokens_db.pop(h, None)


app = FastAPI(title="Recuperação de Senha")


@app.post(
    "/recuperar-senha",
    response_model=MensagemResponse,
    status_code=status.HTTP_200_OK,
)
def recuperar_senha(dados: RecuperarSenhaRequest) -> MensagemResponse:
    limpar_tokens_expirados()

    usuario = usuario_por_email(dados.email)
    if usuario:
        # Invalidar tokens anteriores do mesmo usuário
        user_id = usuario["id"]
        tokens_antigos = [h for h, d in tokens_db.items() if d["usuario_id"] == user_id]
        for h in tokens_antigos:
            tokens_db.pop(h, None)

        # Gerar token criptograficamente seguro e armazenar apenas seu hash (OWASP)
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        tokens_db[token_hash] = {
            "usuario_id": user_id,
            "expira_em": agora() + TOKEN_EXPIRACAO_SEGUNDOS,
        }

        enviar_email(usuario["email"], token)

    # Resposta genérica para mitigar User Enumeration (OWASP)
    return MensagemResponse(
        mensagem="Se o e-mail informado estiver cadastrado, as instruções para redefinição de senha foram enviadas."
    )


@app.post(
    "/redefinir-senha",
    response_model=MensagemResponse,
    status_code=status.HTTP_200_OK,
)
def redefinir_senha(dados: RedefinirSenhaRequest) -> MensagemResponse:
    limpar_tokens_expirados()

    token_hash = hashlib.sha256(dados.token.encode("utf-8")).hexdigest()
    info_token = tokens_db.get(token_hash)

    if not info_token or info_token["expira_em"] <= agora():
        tokens_db.pop(token_hash, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    usuario_id = info_token["usuario_id"]
    definir_senha(usuario_id, dados.nova_senha)

    # Invalidação de uso único do token (OWASP)
    tokens_db.pop(token_hash, None)

    return MensagemResponse(mensagem="Senha redefinida com sucesso.")