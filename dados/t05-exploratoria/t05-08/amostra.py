from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, now
import secrets

app = FastAPI()

# Token info: {token: {'usuario_id': int, 'expira_em': float}}
_tokens: dict[str, dict] = {}

TOKEN_VALIDADE_SEGUNDOS = 3600  # 1 hora

class RecuperarSenhaRequest(BaseModel):
    email: str

class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str

@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest, request: Request):
    usuario = usuario_por_email(req.email)
    if not usuario:
        # Para não vazar info, responde sucesso mesmo se email não existir
        return {"mensagem": "Se o email estiver cadastrado, um token foi enviado."}

    token = secrets.token_urlsafe(32)
    expira_em = now() + TOKEN_VALIDADE_SEGUNDOS
    _tokens[token] = {"usuario_id": usuario['id'], "expira_em": expira_em}

    enviar_email(usuario['email'], token)
    return {"mensagem": "Se o email estiver cadastrado, um token foi enviado."}

@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    data = _tokens.get(req.token)
    if not data or data['expira_em'] < now():
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    definir_senha(data['usuario_id'], req.nova_senha)
    del _tokens[req.token]
    return {"mensagem": "Senha redefinida com sucesso."}