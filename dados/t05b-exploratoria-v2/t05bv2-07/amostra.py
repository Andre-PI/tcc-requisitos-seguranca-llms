import secrets
import hashlib
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from tcc_t05_infra import usuario_por_email, definir_senha, enviar_email, agora

app = FastAPI()

TOKEN_VALIDADE = 900  # segundos

class RecuperarSenhaRequest(BaseModel):
    email: EmailStr

class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str


# token_digest -> {
#   'usuario_id': int,
#   'expira_em': float,
#   'usado': bool
# }
_tokens = {}

def _digest_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


@app.post("/recuperar-senha")
def recuperar_senha(req: RecuperarSenhaRequest):
    # Sempre retorna 200 com mesma mensagem, independente de email existir
    usuario = usuario_por_email(req.email)
    if usuario:
        # gerar token criptograficamente seguro, 32 bytes aleatorios
        token_bytes = secrets.token_bytes(32)
        token = secrets.token_urlsafe(48)  # 48 chars base64url ~ 32 bytes entropy
        token_digest = _digest_token(token)

        _tokens[token_digest] = {
            'usuario_id': usuario['id'],
            'expira_em': agora() + TOKEN_VALIDADE,
            'usado': False
        }
        enviar_email(usuario['email'], token)
    # mesmo retorno para email existente ou não
    return {"mensagem": "Se o e-mail estiver cadastrado, um token foi enviado."}

@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest):
    token_digest = _digest_token(req.token)
    info = _tokens.get(token_digest)
    if (
        info is None or
        info['usado'] or
        agora() > info['expira_em']
    ):
        # token inválido, usado ou expirado
        # 400, 401, 403, 404, 410 ou 422 são aceitos, escolho 410 Gone para expirado e usado
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token inválido, expirado ou já utilizado.")

    # Token válido
    definir_senha(info['usuario_id'], req.nova_senha)
    info['usado'] = True

    return {"mensagem": "Senha redefinida com sucesso."}