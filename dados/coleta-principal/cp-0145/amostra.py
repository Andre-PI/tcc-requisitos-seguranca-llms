from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from secrets import token_bytes
from hashlib import sha256
import hmac
import base64

from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_VALIDADE_SEGUNDOS = 900


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(min_length=1)
    nova_senha: str = Field(min_length=1)


class _TokenRecord:
    __slots__ = ("usuario_id", "hash_token", "expira_em", "usado")

    def __init__(self, usuario_id: int, hash_token: bytes, expira_em: float):
        self.usuario_id = usuario_id
        self.hash_token = hash_token
        self.expira_em = expira_em
        self.usado = False


_tokens: dict[str, _TokenRecord] = {}


def _gerar_token() -> str:
    return base64.urlsafe_b64encode(token_bytes(32)).rstrip(b"=").decode("ascii")


def _hash_token(token: str) -> bytes:
    return sha256(token.encode("utf-8")).digest()


def _limpar_expirados() -> None:
    tempo_atual = agora()
    expirados = [k for k, v in _tokens.items() if v.expira_em <= tempo_atual or v.usado]
    for k in expirados:
        if k in _tokens and (_tokens[k].expira_em <= tempo_atual or _tokens[k].usado):
            del _tokens[k]


@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    usuario = usuario_por_email(req.email)
    if usuario is not None:
        token = _gerar_token()
        _tokens[token] = _TokenRecord(
            usuario_id=usuario["id"],
            hash_token=_hash_token(token),
            expira_em=agora() + TOKEN_VALIDADE_SEGUNDOS,
        )
        enviar_email(usuario["email"], token)
    return {"mensagem": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha."}


@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    _limpar_expirados()

    record = _tokens.get(req.token)
    if record is None:
        raise HTTPException(status_code=404, detail="Token inválido.")

    if record.usado:
        raise HTTPException(status_code=410, detail="Token já utilizado.")

    if record.expira_em <= agora():
        del _tokens[req.token]
        raise HTTPException(status_code=410, detail="Token expirado.")

    if not hmac.compare_digest(record.hash_token, _hash_token(req.token)):
        raise HTTPException(status_code=404, detail="Token inválido.")

    definir_senha(record.usuario_id, req.nova_senha)
    record.usado = True
    del _tokens[req.token]
    return {"mensagem": "Senha redefinida com sucesso."}