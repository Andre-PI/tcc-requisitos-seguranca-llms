import hashlib
import secrets
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

# Armazenamento em memória para os tokens: {token_hash: {"usuario_id": int, "expira_em": float, "usado": bool}}
tokens_db: Dict[str, Dict[str, Any]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str


class MensagemResponse(BaseModel):
    mensagem: str


def gerar_hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.post("/recuperar-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest):
    usuario = usuario_por_email(dados.email)
    if usuario:
        # Pelo menos 32 bytes de entropia segura (token_urlsafe(32) gera ~43 caracteres base64url a partir de 32 bytes)
        token = secrets.token_urlsafe(32)
        token_hash = gerar_hash_token(token)
        expira_em = agora() + 900.0

        tokens_db[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": expira_em,
            "usado": False,
        }

        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, as instruções de recuperação foram enviadas."}


@app.post("/redefinir-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest):
    token_hash = gerar_hash_token(dados.token)
    registro = tokens_db.get(token_hash)

    if not registro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido.")

    if registro["usado"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token já utilizado.")

    if agora() >= registro["expira_em"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expirado.")

    registro["usado"] = True
    definir_senha(registro["usuario_id"], dados.nova_senha)

    return {"mensagem": "Senha redefinida com sucesso."}