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


tokens_db: Dict[str, TokenData] = {}

app = FastAPI()


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, max_length=128)


class MensagemResponse(BaseModel):
    mensagem: str


def _gerar_hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _limpar_tokens_expirados(tempo_atual: float) -> None:
    tokens_para_remover = [
        t_hash
        for t_hash, dados in tokens_db.items()
        if dados["expira_em"] <= tempo_atual
    ]
    for t_hash in tokens_para_remover:
        tokens_db.pop(t_hash, None)


@app.post(
    "/recuperar-senha",
    response_model=MensagemResponse,
    status_code=status.HTTP_200_OK,
)
def recuperar_senha(dados: RecuperarSenhaRequest):
    tempo_atual = agora()
    _limpar_tokens_expirados(tempo_atual)

    usuario = usuario_por_email(dados.email)
    if usuario:
        # Invalida tokens anteriores existentes para este usuario
        tokens_usuario = [
            t_hash
            for t_hash, item in tokens_db.items()
            if item["usuario_id"] == usuario["id"]
        ]
        for t_hash in tokens_usuario:
            tokens_db.pop(t_hash, None)

        token_bruto = secrets.token_urlsafe(32)
        token_hash = _gerar_hash_token(token_bruto)

        tokens_db[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": tempo_atual + TOKEN_EXPIRACAO_SEGUNDOS,
        }

        enviar_email(usuario["email"], token_bruto)

    # Resposta generica para evitar enumeracao de usuarios (OWASP)
    return {
        "mensagem": "Se o e-mail estiver cadastrado, as instruções para redefinição foram enviadas."
    }


@app.post(
    "/redefinir-senha",
    response_model=MensagemResponse,
    status_code=status.HTTP_200_OK,
)
def redefinir_senha(dados: RedefinirSenhaRequest):
    tempo_atual = agora()
    _limpar_tokens_expirados(tempo_atual)

    token_hash = _gerar_hash_token(dados.token)
    registro = tokens_db.get(token_hash)

    if not registro or registro["expira_em"] <= tempo_atual:
        tokens_db.pop(token_hash, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    # Invalida o token imediatamente apos o uso (uso unico)
    tokens_db.pop(token_hash, None)

    definir_senha(registro["usuario_id"], dados.nova_senha)

    return {"mensagem": "Senha redefinida com sucesso."}