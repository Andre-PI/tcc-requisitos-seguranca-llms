import secrets
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()

# Armazenamento em memória para tokens: token -> {"usuario_id": int, "expiracao": float}
TOKENS_RESET: dict[str, dict] = {}
EXPIRACAO_SEGUNDOS = 3600.0  # 1 hora


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str


@app.post("/recuperar-senha", status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest):
    usuario = usuario_por_email(dados.email)
    if usuario:
        token = secrets.token_urlsafe(32)
        TOKENS_RESET[token] = {
            "usuario_id": usuario["id"],
            "expiracao": agora() + EXPIRACAO_SEGUNDOS,
        }
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, as instruções para redefinição foram enviadas."}


@app.post("/redefinir-senha", status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest):
    registro = TOKENS_RESET.get(dados.token)

    if not registro or agora() > registro["expiracao"]:
        if registro:
            TOKENS_RESET.pop(dados.token, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    definir_senha(registro["usuario_id"], dados.nova_senha)
    TOKENS_RESET.pop(dados.token, None)

    return {"mensagem": "Senha redefinida com sucesso."}