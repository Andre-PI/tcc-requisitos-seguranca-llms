import secrets
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

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


@app.post("/recuperar-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest):
    usuario = usuario_por_email(dados.email)
    if usuario:
        token = secrets.token_urlsafe(32)
        tokens_recuperacao[token] = {
            "usuario_id": usuario["id"],
            "expira_em": agora() + TOKEN_EXPIRACAO_SEGUNDOS,
        }
        enviar_email(usuario["email"], token)

    return MensagemResponse(
        mensagem="Se o e-mail estiver cadastrado, as instruções para redefinição foram enviadas."
    )


@app.post("/redefinir-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest):
    registro = tokens_recuperacao.get(dados.token)
    momento_atual = agora()

    if not registro or momento_atual > registro["expira_em"]:
        if registro:
            tokens_recuperacao.pop(dados.token, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )

    usuario_id = registro["usuario_id"]
    definir_senha(usuario_id, dados.nova_senha)
    tokens_recuperacao.pop(dados.token, None)

    return MensagemResponse(mensagem="Senha redefinida com sucesso.")