from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, now
import secrets

app = FastAPI()

class RecuperarSenhaRequest(BaseModel):
    email: EmailStr

class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str

# token -> (usuario_id, expiracao)
_tokens: dict[str, tuple[int, float]] = {}

TOKEN_VIDA_SEGS = 3600  # 1 hora

@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    usuario = usuario_por_email(req.email)
    if not usuario:
        # Para evitar enumeração, reporte sucesso mesmo se não existir
        return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}
    token = secrets.token_urlsafe(32)
    expiracao = now() + TOKEN_VIDA_SEGS
    _tokens[token] = (usuario["id"], expiracao)
    enviar_email(usuario["email"], token)
    return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}

@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    dados = _tokens.get(req.token)
    if not dados:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    usuario_id, expiracao = dados
    if now() > expiracao:
        del _tokens[req.token]
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    definir_senha(usuario_id, req.nova_senha)
    del _tokens[req.token]
    return {"mensagem": "Senha redefinida com sucesso."}