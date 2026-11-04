import os
import hmac
import base64
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, SecretStr, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import IntegrityError

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

app = FastAPI()

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

DB_URL = f"sqlite:///{DB_PATH}"
engine: Engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

# Configurações de hash
PBKDF2_ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "210000"))
PBKDF2_DKLEN = 32
PBKDF2_ALG = "sha256"
SALT_BYTES = 16

# Rate limiting em memória
ACCOUNT_WINDOW_SECONDS = int(os.environ.get("LOGIN_ACCOUNT_WINDOW_SECONDS", "900"))
IP_WINDOW_SECONDS = int(os.environ.get("LOGIN_IP_WINDOW_SECONDS", "900"))
ACCOUNT_MAX_ATTEMPTS = int(os.environ.get("LOGIN_ACCOUNT_MAX_ATTEMPTS", "5"))
IP_MAX_ATTEMPTS = int(os.environ.get("LOGIN_IP_MAX_ATTEMPTS", "20"))

_account_attempts: dict[str, list[float]] = {}
_ip_attempts: dict[str, list[float]] = {}

_dummy_salt = secrets.token_bytes(SALT_BYTES)
_dummy_hash = hashlib.pbkdf2_hmac(
    PBKDF2_ALG,
    b"dummy-password",
    _dummy_salt,
    PBKDF2_ITERATIONS,
    dklen=PBKDF2_DKLEN,
)


class RegistroIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    senha: SecretStr
    nome: str


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    senha: SecretStr


def _now() -> float:
    return time.time()


def _cleanup(bucket: dict[str, list[float]], window: int) -> None:
    cutoff = _now() - window
    for key in list(bucket.keys()):
        bucket[key] = [t for t in bucket[key] if t >= cutoff]
        if not bucket[key]:
            del bucket[key]


def _record_attempt(bucket: dict[str, list[float]], key: str, window: int) -> None:
    _cleanup(bucket, window)
    bucket.setdefault(key, []).append(_now())


def _count_attempts(bucket: dict[str, list[float]], key: str, window: int) -> int:
    _cleanup(bucket, window)
    return len(bucket.get(key, []))


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        PBKDF2_ALG,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=PBKDF2_DKLEN,
    )
    return f"pbkdf2_{PBKDF2_ALG}${PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations_s, salt_b64, hash_b64 = stored.split("$", 3)
        if scheme != f"pbkdf2_{PBKDF2_ALG}":
            return False
        iterations = int(iterations_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except Exception:
        scheme = None
        iterations = PBKDF2_ITERATIONS
        salt = _dummy_salt
        expected = _dummy_hash

    computed = hashlib.pbkdf2_hmac(
        PBKDF2_ALG,
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=len(expected),
    )
    return hmac.compare_digest(computed, expected)


def get_conn() -> Connection:
    return engine.connect()


@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(payload: RegistroIn, request: Request, conn: Connection = Depends(get_conn)):
    senha_hash = _hash_password(payload.senha.get_secret_value())
    try:
        result = conn.execute(
            text(
                "INSERT INTO usuarios (email, senha, nome) "
                "VALUES (:email, :senha, :nome)"
            ),
            {"email": str(payload.email), "senha": senha_hash, "nome": payload.nome},
        )
        conn.commit()
        user_id = result.lastrowid
        return {"id": int(user_id)}
    except IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Usuário já cadastrado")


@app.post("/login")
def login(payload: LoginIn, request: Request, conn: Connection = Depends(get_conn)):
    email = str(payload.email)
    ip = _client_ip(request)

    if _count_attempts(_ip_attempts, ip, IP_WINDOW_SECONDS) >= IP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Tente novamente mais tarde.")

    if _count_attempts(_account_attempts, email, ACCOUNT_WINDOW_SECONDS) >= ACCOUNT_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Tente novamente mais tarde.")

    row = conn.execute(
        text("SELECT id, email, senha, nome FROM usuarios WHERE email = :email"),
        {"email": email},
    ).mappings().first()

    senha_valida = False
    if row:
        senha_valida = _verify_password(payload.senha.get_secret_value(), row["senha"])
    else:
        _verify_password(payload.senha.get_secret_value(), "invalid$0$AA==$AA==")

    if not senha_valida:
        _record_attempt(_account_attempts, email, ACCOUNT_WINDOW_SECONDS)
        _record_attempt(_ip_attempts, ip, IP_WINDOW_SECONDS)
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    return {"id": int(row["id"]), "nome": row["nome"]}