import os
import hmac
import base64
import hashlib
import secrets
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Deque, Dict, Tuple

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

DB_PATH = os.environ.get("TCC_DB_PATH")
if not DB_PATH:
    raise RuntimeError("TCC_DB_PATH não definido")

HASH_ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "210000"))
HASH_NAME = os.environ.get("PASSWORD_HASH_NAME", "sha256")
SALT_BYTES = int(os.environ.get("PASSWORD_HASH_SALT_BYTES", "16"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))
RATE_LIMIT_MAX_PER_ACCOUNT = int(os.environ.get("LOGIN_RATE_LIMIT_MAX_PER_ACCOUNT", "5"))
RATE_LIMIT_MAX_PER_IP = int(os.environ.get("LOGIN_RATE_LIMIT_MAX_PER_IP", "20"))
PEPPER = os.environ.get("PASSWORD_HASH_PEPPER", "")

app = FastAPI()
engine: Engine = create_engine(f"sqlite+pysqlite:///{DB_PATH}", future=True, pool_pre_ping=True)


class RegistroIn(BaseModel):
    email: EmailStr
    senha: SecretStr = Field(min_length=1)
    nome: str = Field(min_length=1, max_length=255)


class LoginIn(BaseModel):
    email: EmailStr
    senha: SecretStr = Field(min_length=1)


@dataclass
class AttemptWindow:
    timestamps: Deque[datetime]


_attempts_by_account: Dict[str, AttemptWindow] = defaultdict(lambda: AttemptWindow(deque()))
_attempts_by_ip: Dict[str, AttemptWindow] = defaultdict(lambda: AttemptWindow(deque()))
_attempts_lock = Lock()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _prune(window: AttemptWindow, now: datetime) -> None:
    cutoff = now - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    dq = window.timestamps
    while dq and dq[0] < cutoff:
        dq.popleft()


def _rate_limited(key: str, store: Dict[str, AttemptWindow], limit: int, now: datetime) -> bool:
    window = store[key]
    _prune(window, now)
    return len(window.timestamps) >= limit


def _register_attempt(key: str, store: Dict[str, AttemptWindow], now: datetime) -> None:
    window = store[key]
    _prune(window, now)
    window.timestamps.append(now)


def _client_ip(request: Request) -> str:
    client = request.client
    return client.host if client and client.host else "unknown"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    pwd = (PEPPER + password).encode("utf-8")
    dk = hashlib.pbkdf2_hmac(HASH_NAME, pwd, salt, HASH_ITERATIONS)
    return f"pbkdf2_{HASH_NAME}${HASH_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iter_s, salt_b64, hash_b64 = stored_hash.split("$", 3)
        if not algo.startswith("pbkdf2_"):
            return False
        hash_name = algo.removeprefix("pbkdf2_")
        iterations = int(iter_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except Exception:
        return False

    pwd = (PEPPER + password).encode("utf-8")
    derived = hashlib.pbkdf2_hmac(hash_name, pwd, salt, iterations)
    return hmac.compare_digest(derived, expected)


def _get_user_by_email(email: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, email, senha, nome FROM usuarios WHERE email = :email"),
            {"email": email},
        ).mappings().first()
        return row


@app.post("/registro", status_code=201)
def registro(payload: RegistroIn):
    email = _normalize_email(str(payload.email))
    senha_hash = _hash_password(payload.senha.get_secret_value())
    nome = payload.nome.strip()

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    "INSERT INTO usuarios (email, senha, nome) "
                    "VALUES (:email, :senha, :nome)"
                ),
                {"email": email, "senha": senha_hash, "nome": nome},
            )
            user_id = result.lastrowid
    except IntegrityError:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    return {"id": int(user_id)}


@app.post("/login")
def login(payload: LoginIn, request: Request):
    email = _normalize_email(str(payload.email))
    senha = payload.senha.get_secret_value()
    ip = _client_ip(request)
    now = _now_utc()

    with _attempts_lock:
        if _rate_limited(email, _attempts_by_account, RATE_LIMIT_MAX_PER_ACCOUNT, now) or _rate_limited(
            ip, _attempts_by_ip, RATE_LIMIT_MAX_PER_IP, now
        ):
            raise HTTPException(status_code=429, detail="Muitas tentativas de login. Tente novamente mais tarde.")

    user = _get_user_by_email(email)

    valid = False
    user_id = None
    nome = None

    if user:
        user_id = user["id"]
        nome = user["nome"]
        valid = _verify_password(senha, user["senha"])
    else:
        _verify_password(senha, _hash_password("dummy-password-for-timing"))

    with _attempts_lock:
        _register_attempt(email, _attempts_by_account, now)
        _register_attempt(ip, _attempts_by_ip, now)

    if not valid:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    return {"id": int(user_id), "nome": nome}