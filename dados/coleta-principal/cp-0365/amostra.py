import hashlib
import secrets
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

# Armazenamento em memória dos tokens vinculados às contas
# Chave: hash SHA-256 do token (str hex)
# Valor: dict contendo 'usuario_id', 'expira_em' e 'usado'
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
        token = secrets.token_urlsafe(32)
        token_hash = _gerar_hash_token(token)
        tempo_atual = agora()
        tokens_db[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": tempo_atual + 900.0,
            "usado": False,
        }
        enviar_email(usuario["email"], token)

    return MensagemResponse(
        mensagem="Se o e-mail estiver cadastrado, as instruções para redefinição de senha foram enviadas."
    )


@app.post("/redefinir-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest):
    token_hash = _gerar_hash_token(dados.token)
    registro = tokens_db.get(token_hash)

    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido, expirado ou já utilizado.",
        )

    if registro["usado"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido, expirado ou já utilizado.",
        )

    tempo_atual = agora()
    if tempo_atual >= registro["expira_em"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido, expirado ou já utilizado.",
        )

    registro["usado"] = True
    definir_senha(registro["usuario_id"], dados.nova_senha)

    return MensagemResponse(mensagem="Senha redefinida com sucesso.")