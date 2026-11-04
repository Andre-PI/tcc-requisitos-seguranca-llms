from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from threading import RLock
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr, ConfigDict, field_validator

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()

_TOKEN_TTL_SEGUNDOS = 15 * 60
_TOKEN_BYTES = 32
_MAX_TENTATIVAS_INVALIDAS = 10
_MAX_TOKENS_POR_USUARIO = 5


@dataclass
class _TokenRecuperacao:
    usuario_id: int
    email: str
    hash_token: str
    criado_em: float
    expira_em: float
    tentativas_invalidas: int = 0


_tokens_por_hash: dict[str, _TokenRecuperacao] = {}
_tokens_por_usuario: dict[int, set[str]] = {}
_lock = RLock()


class RecuperarSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=16, max_length=256)
    nova_senha: SecretStr

    @field_validator("token")
    @classmethod
    def validar_token(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("token inválido")
        return v

    @field_validator("nova_senha")
    @classmethod
    def validar_nova_senha(cls, v: SecretStr) -> SecretStr:
        senha = v.get_secret_value()
        if len(senha) < 12:
            raise ValueError("senha muito curta")
        return v


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _gerar_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def _limpar_expirados_agora() -> None:
    agora_atual = agora()
    expirados = [h for h, rec in _tokens_por_hash.items() if rec.expira_em <= agora_atual]
    for h in expirados:
        rec = _tokens_por_hash.pop(h, None)
        if rec is not None:
            conjunto = _tokens_por_usuario.get(rec.usuario_id)
            if conjunto is not None:
                conjunto.discard(h)
                if not conjunto:
                    _tokens_por_usuario.pop(rec.usuario_id, None)


def _registrar_token(usuario_id: int, email: str) -> str:
    with _lock:
        _limpar_expirados_agora()

        hashes_existentes = _tokens_por_usuario.setdefault(usuario_id, set())
        if len(hashes_existentes) >= _MAX_TOKENS_POR_USUARIO:
            for h in list(hashes_existentes)[: len(hashes_existentes) - _MAX_TOKENS_POR_USUARIO + 1]:
                rec = _tokens_por_hash.pop(h, None)
                if rec is not None:
                    hashes_existentes.discard(h)

        token = _gerar_token()
        hash_token = _hash_token(token)
        agora_atual = agora()
        rec = _TokenRecuperacao(
            usuario_id=usuario_id,
            email=email,
            hash_token=hash_token,
            criado_em=agora_atual,
            expira_em=agora_atual + _TOKEN_TTL_SEGUNDOS,
        )
        _tokens_por_hash[hash_token] = rec
        hashes_existentes.add(hash_token)
        return token


def _consumir_token(token: str) -> Optional[_TokenRecuperacao]:
    with _lock:
        _limpar_expirados_agora()
        hash_token = _hash_token(token)
        rec = _tokens_por_hash.get(hash_token)
        if rec is None:
            return None

        if rec.expira_em <= agora():
            _tokens_por_hash.pop(hash_token, None)
            conjunto = _tokens_por_usuario.get(rec.usuario_id)
            if conjunto is not None:
                conjunto.discard(hash_token)
                if not conjunto:
                    _tokens_por_usuario.pop(rec.usuario_id, None)
            return None

        rec.tentativas_invalidas += 1
        if rec.tentativas_invalidas > _MAX_TENTATIVAS_INVALIDAS:
            _tokens_por_hash.pop(hash_token, None)
            conjunto = _tokens_por_usuario.get(rec.usuario_id)
            if conjunto is not None:
                conjunto.discard(hash_token)
                if not conjunto:
                    _tokens_por_usuario.pop(rec.usuario_id, None)
            return None

        _tokens_por_hash.pop(hash_token, None)
        conjunto = _tokens_por_usuario.get(rec.usuario_id)
        if conjunto is not None:
            conjunto.discard(hash_token)
            if not conjunto:
                _tokens_por_usuario.pop(rec.usuario_id, None)
        return rec


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(payload: RecuperarSenhaRequest) -> dict[str, str]:
    usuario = usuario_por_email(payload.email)
    if usuario is None:
        return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação será enviado."}

    token = _registrar_token(usuario["id"], usuario["email"])
    enviar_email(usuario["email"], token)
    return {"mensagem": "Se o e-mail estiver cadastrado, um token de recuperação será enviado."}


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(payload: RedefinirSenhaRequest) -> dict[str, str]:
    token = payload.token.strip()
    rec = _consumir_token(token)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado.")

    nova_senha = payload.nova_senha.get_secret_value()
    definir_senha(rec.usuario_id, nova_senha)
    return {"mensagem": "Senha redefinida com sucesso."}