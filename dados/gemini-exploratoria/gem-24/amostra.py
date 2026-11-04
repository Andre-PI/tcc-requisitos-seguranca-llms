import hashlib
import secrets
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

# Armazenamento em memória dos tokens:
# { token_hash: {"usuario_id": int, "expira_em": float, "usado": bool} }
tokens_db = {}


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str


class MensagemResponse(BaseModel):
    mensagem: str


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.post("/recuperar-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def recuperar_senha(dados: RecuperarSenhaRequest):
    usuario = usuario_por_email(dados.email)
    if usuario:
        # Gera token criptograficamente seguro com pelo menos 32 bytes aleatórios
        token = secrets.token_urlsafe(32)
        h = hash_token(token)
        expira_em = agora() + 900.0
        tokens_db[h] = {
            "usuario_id": usuario["id"],
            "expira_em": expira_em,
            "usado": False,
        }
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, as instruções de recuperação foram enviadas."}


@app.post("/redefinir-senha", response_model=MensagemResponse, status_code=status.HTTP_200_OK)
def redefinir_senha(dados: RedefinirSenhaRequest):
    h = hash_token(dados.token)
    registro = tokens_db.get(h)

    # Rejeita token inexistente
    if not registro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado.")

    # Rejeita token já utilizado
    if registro["usado"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado.")

    # Rejeita a partir do instante de expiração (validade de 900 segundos)
    if agora() >= registro["expira_em"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado.")

    # Invalida o token imediatamente
    registro["usado"] = True

    # Atualiza a senha da conta vinculada
    definir_senha(registro["usuario_id"], dados.nova_senha)

    return {"mensagem": "Senha redefinida com sucesso."}