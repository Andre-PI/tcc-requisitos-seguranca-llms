from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field, constr
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora
import secrets
from typing import Dict

app = FastAPI()

# token -> (usuario_id, expiracao)
_tokens: Dict[str, tuple[int, float]] = {}
TOKEN_TTL = 3600  # 1 hora


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: constr(min_length=1)
    nova_senha: constr(min_length=6)


@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    usuario = usuario_por_email(req.email)
    if usuario is None:
        # Para segurança não informar se email existe ou não
        return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}

    token = secrets.token_urlsafe(32)
    expiracao = agora() + TOKEN_TTL
    _tokens[token] = (usuario["id"], expiracao)

    enviar_email(usuario["email"], token)
    return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}


@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    dados = _tokens.get(req.token)
    if not dados:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    usuario_id, expiracao = dados
    if agora() > expiracao:
        del _tokens[req.token]
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    definir_senha(usuario_id, req.nova_senha)
    del _tokens[req.token]
    return {"mensagem": "Senha redefinida com sucesso."}