from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Tuple
import secrets

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

# token -> (usuario_id, email, expira_em)
_tokens: Dict[str, Tuple[int, str, float]] = {}
_TTL_SEGUNDOS = 3600.0


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


def _limpar_tokens_expirados() -> None:
    tempo_atual = agora()
    expirados = [token for token, (_, _, expira_em) in _tokens.items() if expira_em <= tempo_atual]
    for token in expirados:
        del _tokens[token]


@app.post("/recuperar-senha")
def recuperar_senha(payload: RecuperarSenhaRequest):
    _limpar_tokens_expirados()

    usuario = usuario_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = secrets.token_urlsafe(32)
    _tokens[token] = (usuario["id"], usuario["email"], agora() + _TTL_SEGUNDOS)
    enviar_email(usuario["email"], token)

    return {"mensagem": "Token de recuperação enviado com sucesso."}


@app.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest):
    _limpar_tokens_expirados()

    dados = _tokens.get(payload.token)
    if dados is None:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    usuario_id, _, _ = dados
    definir_senha(usuario_id, payload.nova_senha)
    del _tokens[payload.token]

    return {"mensagem": "Senha redefinida com sucesso."}