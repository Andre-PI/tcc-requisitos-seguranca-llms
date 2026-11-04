import os
import time
import hmac
import hashlib
import secrets
import logging
from collections import deque, defaultdict
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

app = FastAPI()

logger = logging.getLogger("auth")
logger.addHandler(logging.NullHandler())
logger.propagate = False

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH must be defined before import")

DB_URL = f"sqlite:///{DB_PATH}"
engine: Engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

# ---- Password hashing (custom, with configurable cost) ----
PASSWORD_HASH_ALGO = "pbkdf2_sha256"
PASSWORD_COST = int(os.environ.get("PASSWORD_COST", "200000"))
PASSWORD_SALT_BYTES = int(os.environ.get("PASSWORD_SALT_BYTES", "16"))

def hash_password(password: str, salt: bytes | None = None, cost: int | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    if cost is None:
        cost = PASSWORD_COST
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, cost)
    return f"{PASSWORD_HASH_ALGO}${cost}${salt.hex()}${dk.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, cost_s, salt_hex, dk_hex = stored_hash.split("$", 3)
        if algo != PASSWORD_HASH_ALGO:
            return False
        cost = int(cost_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(dk_hex)
    except Exception:
        # Keep constant-time-ish behavior even for malformed stored values
        dummy = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            b"\x00" * PASSWORD_SALT_BYTES,
            PASSWORD_COST,
        )
        return hmac.compare_digest(dummy, b"\x00" * len(dummy))
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, cost)
    return hmac.compare_digest(candidate, expected)

# ---- Rate limiting ----
LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "300"))
LOGIN_MAX_ATTEMPTS_PER_ACCOUNT = int(os.environ.get("LOGIN_MAX_ATTEMPTS_PER_ACCOUNT", "5"))
LOGIN_MAX_ATTEMPTS_PER_IP = int(os.environ.get("LOGIN_MAX_ATTEMPTS_PER_IP", "20"))

@dataclass
class AttemptBucket:
    timestamps: deque

_rate_by_account: dict[str, AttemptBucket] = defaultdict(lambda: AttemptBucket(deque()))
_rate_by_ip: dict[str, AttemptBucket] = defaultdict(lambda: AttemptBucket(deque()))
_rate_lock = None

def _now() -> float:
    return time.monotonic()

def _prune(bucket: deque, now: float) -> None:
    cutoff = now - LOGIN_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()

def _rate_limited(key: str, store: dict[str, AttemptBucket], limit: int) -> bool:
    now = _now()
    bucket = store[key].timestamps
    _prune(bucket, now)
    return len(bucket) >= limit

def _register_attempt(key: str, store: dict[str, AttemptBucket]) -> None:
    now = _now()
    bucket = store[key].timestamps
    _prune(bucket, now)
    bucket.append(now)

def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"

# ---- Schemas ----
class RegistroIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)
    nome: str = Field(min_length=1)

class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)

class RegistroOut(BaseModel):
    id: int

class LoginOut(BaseModel):
    id: int
    nome: str

# ---- Helpers ----
def _get_user_by_email(email: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, email, senha, nome FROM usuarios WHERE email = :email"),
            {"email": email},
        ).mappings().first()
        return row

def _insert_user(email: str, senha_hash: str, nome: str) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO usuarios (email, senha, nome) "
                "VALUES (:email, :senha, :nome)"
            ),
            {"email": email, "senha": senha_hash, "nome": nome},
        )
        return int(result.lastrowid)

def _authenticate(email: str, senha: str) -> tuple[int, str] | None:
    user = _get_user_by_email(email)
    if not user:
        # Dummy verification to reduce timing differences
        _ = verify_password(senha, hash_password("dummy-password"))
        return None
    if not verify_password(senha, user["senha"]):
        return None
    return int(user["id"]), str(user["nome"])

# ---- Routes ----
@app.post("/registro", status_code=status.HTTP_201_CREATED, response_model=RegistroOut)
def registro(payload: RegistroIn):
    senha_hash = hash_password(payload.senha)
    try:
        user_id = _insert_user(payload.email, senha_hash, payload.nome)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="email já cadastrado")
    return {"id": user_id}

@app.post("/login", response_model=LoginOut)
def login(payload: LoginIn, request: Request):
    ip = get_client_ip(request)
    email_key = payload.email.lower()

    if _rate_limited(email_key, _rate_by_account, LOGIN_MAX_ATTEMPTS_PER_ACCOUNT) or _rate_limited(
        ip, _rate_by_ip, LOGIN_MAX_ATTEMPTS_PER_IP
    ):
        raise HTTPException(status_code=401, detail="credenciais inválidas")

    _register_attempt(email_key, _rate_by_account)
    _register_attempt(ip, _rate_by_ip)

    auth = _authenticate(payload.email, payload.senha)
    if auth is None:
        raise HTTPException(status_code=401, detail="credenciais inválidas")

    user_id, nome = auth
    return {"id": user_id, "nome": nome}