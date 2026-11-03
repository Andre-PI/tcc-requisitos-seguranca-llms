import secrets
import hashlib
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

# Token info structure:
# token_hash: str -> sha256 hex digest of token bytes
# stored as key in tokens dict
# value: dict with keys: usuario_id: int, criado_em: float (segundos unix), usado: bool

tokens: dict[str, dict] = {}

TOKEN_EXPIRACAO_SEG = 900

class RecuperarSenhaRequest(BaseModel):
    email: str

class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str

@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    # Sempre retorna 200 e JSON idêntico, mesmo se email não existir
    usuario = usuario_por_email(req.email)
    if usuario is not None:
        # Gerar token criptograficamente seguro, 32 bytes
        token_bytes = secrets.token_bytes(32)
        token = token_bytes.hex()
        token_hash = hashlib.sha256(token_bytes).hexdigest()
        # Armazenar token hash com dados
        tokens[token_hash] = {
            "usuario_id": usuario["id"],
            "criado_em": agora(),
            "usado": False,
        }
        enviar_email(usuario["email"], token)
    # Resposta igual para email existente ou não
    return {"mensagem": "Caso o email exista no sistema, instruções foram enviadas."}

@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    token_str = req.token
    # token é hex string, deve ter comprimento 64 (32 bytes * 2)
    if len(token_str) != 64:
        raise HTTPException(status_code=400, detail="Token inválido")
    try:
        token_bytes = bytes.fromhex(token_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Token inválido")
    token_hash = hashlib.sha256(token_bytes).hexdigest()
    token_data = tokens.get(token_hash)
    if token_data is None:
        # Token não existe
        raise HTTPException(status_code=404, detail="Token não encontrado")
    if token_data["usado"]:
        # Token já usado
        raise HTTPException(status_code=410, detail="Token já usado")
    agora_seg = agora()
    if agora_seg > token_data["criado_em"] + TOKEN_EXPIRACAO_SEG:
        # Token expirado
        # Invalida token para não reutilização
        token_data["usado"] = True
        raise HTTPException(status_code=403, detail="Token expirado")
    # Token válido, redefine senha
    definir_senha(token_data["usuario_id"], req.nova_senha)
    # Invalida token após uso
    token_data["usado"] = True
    return {"mensagem": "Senha redefinida com sucesso."}