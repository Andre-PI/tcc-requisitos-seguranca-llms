from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, constr, ValidationError
from typing import Dict
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora
import secrets
import threading

app = FastAPI()

# Token data: token -> (usuario_id, expiracao)
_tokens: Dict[str, tuple[int, float]] = {}
_lock = threading.Lock()
TOKEN_EXPIRATION_SECONDS = 3600  # 1 hora

class RecuperarSenhaRequest(BaseModel):
    email: EmailStr

class RedefinirSenhaRequest(BaseModel):
    token: constr(min_length=32, max_length=64)
    nova_senha: constr(min_length=8)

def _limpar_tokens_expirados() -> None:
    now = agora()
    with _lock:
        expirados = [t for t, (_, exp) in _tokens.items() if exp < now]
        for t in expirados:
            _tokens.pop(t, None)

@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    _limpar_tokens_expirados()
    usuario = usuario_por_email(req.email)
    if usuario is None:
        # Para segurança, retornar mensagem genérica
        return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}
    token = secrets.token_urlsafe(48)
    expiracao = agora() + TOKEN_EXPIRATION_SECONDS
    with _lock:
        _tokens[token] = (usuario["id"], expiracao)
    enviar_email(usuario["email"], token)
    return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}

@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    _limpar_tokens_expirados()
    with _lock:
        token_data = _tokens.get(req.token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido ou expirado."
            )
        usuario_id, expiracao = token_data
        if expiracao < agora():
            _tokens.pop(req.token, None)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido ou expirado."
            )
        # Token válido, apagar para evitar reutilização
        _tokens.pop(req.token)
    definir_senha(usuario_id, req.nova_senha)
    return {"mensagem": "Senha redefinida com sucesso."}