import hashlib
import secrets
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

# Armazenamento em memória dos tokens: hash -> {usuario_id, expira_em, usado}
tokens_db: Dict[str, Dict[str, Any]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str


class MensagemResponse(BaseModel):
    mensagem: str


def _gerar_hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.post("/recuperar-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest):
    usuario = usuario_por_email(dados.email)
    if usuario is not None:
        # Gera token criptograficamente seguro com pelo menos 32 bytes aleatórios
        token = secrets.token_urlsafe(32)
        token_hash = _gerar_hash_token(token)
        expira_em = agora() + 900.0

        tokens_db[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": expira_em,
            "usado": False,
        }

        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, um link de recuperação será enviado."}


@app.post("/redefinir-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest):
    token_hash = _gerar_hash_token(dados.token)
    registro = tokens_db.get(token_hash)

    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado."
        )

    if registro["usado"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado."
        )

    # Rejeitando a partir do instante de expiração (expira_em <= agora())
    if agora() >= registro["expira_em"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado."
        )

    # Invalida o token imediatamente
    registro["usado"] = True

    # Atualiza a senha do usuário vinculado
    definir_senha(registro["usuario_id"], dados.nova_senha)

    return {"mensagem": "Senha redefinida com sucesso."}