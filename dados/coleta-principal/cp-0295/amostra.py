from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr
from typing import Dict, Tuple
import secrets
import hashlib

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

_TOKEN_TTL_SEGUNDOS = 15 * 60
_TOKENS: Dict[str, Tuple[int, float]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    nova_senha: SecretStr = Field(min_length=8, max_length=256)


def _limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    expirados = [token for token, (_, expira_em) in _TOKENS.items() if expira_em <= tempo_atual]
    for token in expirados:
        _TOKENS.pop(token, None)


def _gerar_token() -> str:
    return secrets.token_urlsafe(32)


def _validar_forca_senha(senha: str) -> None:
    if len(senha) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha inválida")
    if len(senha) > 256:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha inválida")
    if senha.strip() != senha:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha inválida")


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(payload.email)
    if usuario is None:
        return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha."}

    token = _gerar_token()
    _TOKENS[token] = (int(usuario["id"]), agora() + _TOKEN_TTL_SEGUNDOS)
    enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha."}


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    token = payload.token.strip()
    nova_senha = payload.nova_senha.get_secret_value()

    _validar_forca_senha(nova_senha)

    dados_token = _TOKENS.pop(token, None)
    if dados_token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    usuario_id, expira_em = dados_token
    if expira_em <= agora():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    definir_senha(usuario_id, nova_senha)
    return {"mensagem": "Senha redefinida com sucesso"}