import secrets
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from tcc_t05_infra import agora, definir_senha, enviar_email, usuario_por_email

app = FastAPI()

TOKEN_EXPIRACAO_SEGUNDOS = 3600
tokens_recuperacao: dict[str, dict] = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str


class MensagemResponse(BaseModel):
    mensagem: str


@app.post("/recuperar-senha", response_model=MensagemResponse)
def recuperar_senha(dados: RecuperarSenhaRequest):
    usuario = usuario_por_email(dados.email)
    if usuario:
        token = secrets.token_urlsafe(32)
        tokens_recuperacao[token] = {
            "usuario_id": usuario["id"],
            "expira_em": agora() + TOKEN_EXPIRACAO_SEGUNDOS,
        }
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, as instruções foram enviadas."}


@app.post("/redefinir-senha", response_model=MensagemResponse)
def redefinir_senha(dados: RedefinirSenhaRequest):
    info_token = tokens_recuperacao.get(dados.token)

    if not info_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    if agora() > info_token["expira_em"]:
        del tokens_recuperacao[dados.token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    definir_senha(info_token["usuario_id"], dados.nova_senha)
    del tokens_recuperacao[dados.token]

    return {"mensagem": "Senha redefinida com sucesso."}