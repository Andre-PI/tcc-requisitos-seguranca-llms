from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora
import secrets

app = FastAPI()

# token_storage: token -> dict with keys: usuario_id, expiracao (float timestamp)
token_storage: dict[str, dict[str, object]] = {}

TOKEN_VALIDITY_SECONDS = 3600  # 1 hour


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: constr(min_length=1)
    nova_senha: constr(min_length=1)


@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    usuario = usuario_por_email(req.email)
    if usuario is None:
        # For security, respond success even if user not found
        return {"mensagem": "Se o email estiver cadastrado, um token foi enviado."}
    token = secrets.token_urlsafe(32)
    expiracao = agora() + TOKEN_VALIDITY_SECONDS
    token_storage[token] = {"usuario_id": usuario["id"], "expiracao": expiracao}
    enviar_email(usuario["email"], token)
    return {"mensagem": "Se o email estiver cadastrado, um token foi enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    dados_token = token_storage.get(req.token)
    if not dados_token:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    if dados_token["expiracao"] < agora():
        del token_storage[req.token]
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    definir_senha(dados_token["usuario_id"], req.nova_senha)
    del token_storage[req.token]
    return {"mensagem": "Senha redefinida com sucesso."}