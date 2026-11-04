import hashlib
import hmac
import secrets
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()

TOKEN_EXPIRACAO_SEGUNDOS = 900  # 15 minutos

# Armazenamento em memória para tokens: {token_hash: {"usuario_id": int, "expira_em": float}}
tokens_recuperacao: dict[str, dict] = {}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, max_length=128)


class RespostaPadrao(BaseModel):
    mensagem: str


@app.post("/recuperar-senha", response_model=RespostaPadrao, status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest) -> RespostaPadrao:
    usuario = usuario_por_email(dados.email)
    tempo_atual = agora()

    if usuario is not None:
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)

        # Invalida tokens anteriores do mesmo usuário
        tokens_a_remover = [
            th for th, info in tokens_recuperacao.items()
            if info["usuario_id"] == usuario["id"] or info["expira_em"] < tempo_atual
        ]
        for th in tokens_a_remover:
            tokens_recuperacao.pop(th, None)

        tokens_recuperacao[token_hash] = {
            "usuario_id": usuario["id"],
            "expira_em": tempo_atual + TOKEN_EXPIRACAO_SEGUNDOS,
        }

        enviar_email(usuario["email"], token)
    else:
        # Limpeza periódica de tokens expirados mesmo se o usuário não for encontrado
        tokens_expirados = [
            th for th, info in tokens_recuperacao.items()
            if info["expira_em"] < tempo_atual
        ]
        for th in tokens_expirados:
            tokens_recuperacao.pop(th, None)

    # Mensagem genérica para prevenir enumeração de usuários (OWASP)
    return RespostaPadrao(
        mensagem="Se o e-mail estiver cadastrado, as instruções para redefinição de senha foram enviadas."
    )


@app.post("/redefinir-senha", response_model=RespostaPadrao, status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest) -> RespostaPadrao:
    token_hash = _hash_token(dados.token)
    info_token = None
    chave_encontrada = None

    tempo_atual = agora()

    # Comparação em tempo constante para mitigar timing attacks
    for th, info in list(tokens_recuperacao.items()):
        if hmac.compare_digest(th, token_hash):
            info_token = info
            chave_encontrada = th
            break

    if info_token is None or info_token["expira_em"] < tempo_atual:
        if chave_encontrada:
            tokens_recuperacao.pop(chave_encontrada, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    usuario_id = info_token["usuario_id"]
    tokens_recuperacao.pop(chave_encontrada, None)

    definir_senha(usuario_id, dados.nova_senha)

    return RespostaPadrao(mensagem="Senha redefinida com sucesso.")