import hashlib
import secrets
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

# Armazenamento em memória para os tokens de recuperação:
# token_hash -> {"usuario_id": int, "expira_em": float, "usado": bool}
tokens_db: Dict[str, Dict[str, Any]] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str


class MensagemResponse(BaseModel):
    mensagem: str


@app.post("/recuperar-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest):
    usuario = usuario_por_email(dados.email)
    if usuario:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        tempo_atual = agora()
        tokens_db[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": tempo_atual + 900.0,
            "usado": False,
        }
        enviar_email(usuario["email"], token)

    return MensagemResponse(
        mensagem="Se o e-mail informado estiver cadastrado, as instruções para recuperação de senha foram enviadas."
    )


@app.post("/redefinir-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest):
    token_hash = hashlib.sha256(dados.token.encode("utf-8")).hexdigest()
    registro = tokens_db.get(token_hash)

    if not registro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou inexistente."
        )

    if registro["usado"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token já utilizado."
        )

    if agora() >= registro["expira_em"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token expirado."
        )

    registro["usado"] = True
    definir_senha(registro["usuario_id"], dados.nova_senha)

    return MensagemResponse(mensagem="Senha redefinida com sucesso.")