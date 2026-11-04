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
_tokens_db: Dict[str, TokenData] = {}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, max_length=128)


class MensagemResponse(BaseModel):
    mensagem: str


app = FastAPI()


@app.post("/recuperar-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest) -> MensagemResponse:
    usuario = usuario_por_email(dados.email)
    if usuario:
        # Gerar token criptograficamente seguro com alta entropia
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        _tokens_db[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": agora() + TOKEN_EXPIRATION_SECONDS,
        }
        enviar_email(usuario["email"], token)

    # Resposta genérica para evitar enumeração de usuários (OWASP)
    return MensagemResponse(
        mensagem="Se o e-mail estiver cadastrado, as instruções de recuperação foram enviadas."
    )


@app.post("/redefinir-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest) -> MensagemResponse:
    token_hash = _hash_token(dados.token)
    token_info = _tokens_db.get(token_hash)

    # Validação do token e expiração
    if not token_info or agora() > token_info["expira_em"]:
        if token_info:
            _tokens_db.pop(token_hash, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    # Invalidação do token para garantir uso único (OWASP)
    _tokens_db.pop(token_hash, None)

    # Atualização da senha via infraestrutura
    definir_senha(token_info["usuario_id"], dados.nova_senha)

    return MensagemResponse(mensagem="Senha redefinida com sucesso.")