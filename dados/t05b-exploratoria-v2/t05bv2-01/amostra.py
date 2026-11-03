from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, constr
from typing import Dict
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

# armazenamento em memoria dos tokens: token -> {'usuario_id': int, 'expira': float}
_tokens: Dict[str, dict] = {}

TOKEN_EXPIRACAO_SEGUNDOS = 3600  # 1 hora


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: constr(min_length=1)
    nova_senha: constr(min_length=6)


@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    usuario = usuario_por_email(req.email)
    if usuario:
        token = secrets.token_urlsafe(32)
        _tokens[token] = {
            "usuario_id": usuario["id"],
            "expira": agora() + TOKEN_EXPIRACAO_SEGUNDOS,
        }
        enviar_email(usuario["email"], token)
    # Sempre retorna sucesso para não vazar info de usuario
    return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    info = _tokens.get(req.token)
    if not info or info["expira"] < agora():
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    definir_senha(info["usuario_id"], req.nova_senha)
    del _tokens[req.token]
    return {"mensagem": "Senha redefinida com sucesso."}