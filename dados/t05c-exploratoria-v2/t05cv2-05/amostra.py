import secrets
import hashlib
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, EmailStr, constr
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

class RecuperarSenhaRequest(BaseModel):
    email: EmailStr

class RedefinirSenhaRequest(BaseModel):
    token: constr(min_length=64, max_length=64)
    nova_senha: constr(min_length=1)

# token storage: token_hash -> {usuario_id:int, exp:float, usado:bool}
_tokens: dict[str, dict] = {}

TOKEN_VALIDADE = 900.0  # segundos

def _hash_token(token: str) -> str:
    # SHA256 hex digest
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    usuario = usuario_por_email(req.email)
    # Sempre responda igual, mesmo para emails inexistentes

    if usuario is not None:
        # gerar token criptograficamente seguro, 32 bytes aleatorios
        token_bytes = secrets.token_bytes(32)
        token = token_bytes.hex()
        token_hash = _hash_token(token)
        agora_ts = agora()
        _tokens[token_hash] = {
            "usuario_id": usuario["id"],
            "exp": agora_ts + TOKEN_VALIDADE,
            "usado": False,
        }
        enviar_email(usuario["email"], token)

    return {"mensagem": "Se o e-mail estiver cadastrado, um link para redefinir a senha foi enviado."}

@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    token_hash = _hash_token(req.token)
    info = _tokens.get(token_hash)
    agora_ts = agora()

    if info is None:
        raise HTTPException(status_code=404, detail="Token inválido ou inexistente.")
    if info["usado"]:
        raise HTTPException(status_code=410, detail="Token já usado.")
    if agora_ts > info["exp"]:
        raise HTTPException(status_code=410, detail="Token expirado.")

    definir_senha(info["usuario_id"], req.nova_senha)
    info["usado"] = True

    return {"mensagem": "Senha redefinida com sucesso."}