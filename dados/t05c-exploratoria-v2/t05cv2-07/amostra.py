from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, constr, ValidationError
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora
from typing import Dict
import secrets
import time

app = FastAPI()

# Token validade: 1 hora (3600 segundos)
TOKEN_EXPIRACAO = 3600

# Estrutura para armazenar tokens em memória: token -> (usuario_id, timestamp)
_tokens: Dict[str, tuple[int, float]] = {}

class RecuperarSenhaRequest(BaseModel):
    email: EmailStr

class RedefinirSenhaRequest(BaseModel):
    token: constr(min_length=32, max_length=128)
    nova_senha: constr(min_length=8, max_length=128)

def _limpar_tokens_expirados() -> None:
    agora_ts = agora()
    expirados = [t for t, (_, ts) in _tokens.items() if agora_ts - ts > TOKEN_EXPIRACAO]
    for t in expirados:
        del _tokens[t]

@app.post("/recuperar-senha", status_code=200)
def recuperar_senha(req: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(req.email)
    # Não informar se o email não existe (boa prática para evitar enumeração)
    if usuario:
        token = secrets.token_urlsafe(48)
        _tokens[token] = (usuario["id"], agora())
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, um token para redefinição foi enviado."}

@app.post("/redefinir-senha", status_code=200)
def redefinir_senha(req: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    dados = _tokens.get(req.token)
    if not dados:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado.")

    usuario_id, ts = dados
    if agora() - ts > TOKEN_EXPIRACAO:
        del _tokens[req.token]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expirado.")

    try:
        definir_senha(usuario_id, req.nova_senha)
    except Exception:
        # Em caso de falha na alteração, erro genérico
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao redefinir senha.")

    del _tokens[req.token]

    return {"mensagem": "Senha redefinida com sucesso."}