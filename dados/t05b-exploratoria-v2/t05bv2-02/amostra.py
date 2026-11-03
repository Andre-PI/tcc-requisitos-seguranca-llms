from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, constr
from typing import Dict
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, now

app = FastAPI()

# Token validade em segundos (ex: 1h)
TOKEN_VALIDADE = 3600

class RecuperarSenhaRequest(BaseModel):
    email: EmailStr

class RedefinirSenhaRequest(BaseModel):
    token: constr(min_length=1)
    nova_senha: constr(min_length=6)

# tokens armazenados em memória: token -> {usuario_id, expiracao}
_tokens: Dict[str, Dict[str, float]] = {}

import secrets

@app.post("/recuperar-senha")
def recuperar_senha(dados: RecuperarSenhaRequest):
    usuario = usuario_por_email(dados.email)
    if usuario is None:
        # Para não vazar info, responder sucesso mesmo assim
        return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}
    token = secrets.token_urlsafe(32)
    expiracao = now() + TOKEN_VALIDADE
    _tokens[token] = {"usuario_id": usuario["id"], "expiracao": expiracao}
    enviar_email(usuario["email"], token)
    return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}

@app.post("/redefinir-senha")
def redefinir_senha(dados: RedefinirSenhaRequest):
    info = _tokens.get(dados.token)
    if not info or info["expiracao"] < now():
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")
    definir_senha(info["usuario_id"], dados.nova_senha)
    del _tokens[dados.token]
    return {"mensagem": "Senha redefinida com sucesso."}