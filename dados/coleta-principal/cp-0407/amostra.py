from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Path, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator
from threading import Lock

app = FastAPI(title="Perfil Público")

_store: dict[int, dict[str, str]] = {}
_next_id = 1
_lock = Lock()

_ALLOWED_SCHEMES = {"http", "https"}
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


class PerfilIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=200)
    bio: str = Field(min_length=1, max_length=5000)
    site: str = Field(min_length=1, max_length=2048)

    @field_validator("nome", "bio", "site")
    @classmethod
    def no_control_chars(cls, v: str) -> str:
        if _CONTROL_CHARS_RE.search(v):
            raise ValueError("caracteres de controle não são permitidos")
        return v.strip()

    @field_validator("site")
    @classmethod
    def validate_site(cls, v: str) -> str:
        try:
            parsed = urlparse(v)
        except Exception as exc:
            raise ValueError("URL inválida") from exc

        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            raise ValueError("esquema de URL não permitido")
        if not parsed.netloc:
            raise ValueError("URL inválida")
        if any(c.isspace() for c in v):
            raise ValueError("URL inválida")

        return v


class PerfilOut(BaseModel):
    id: int


@app.post("/perfil", status_code=status.HTTP_201_CREATED, response_model=PerfilOut)
def criar_perfil(perfil: PerfilIn) -> Any:
    global _next_id
    with _lock:
        perfil_id = _next_id
        _next_id += 1
        _store[perfil_id] = {
            "nome": perfil.nome,
            "bio": perfil.bio,
            "site": perfil.site,
        }
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(
    perfil_id: int = Path(..., ge=1),
) -> HTMLResponse:
    perfil = _store.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    nome = html.escape(perfil["nome"], quote=True)
    bio = html.escape(perfil["bio"], quote=True)
    site = html.escape(perfil["site"], quote=True)

    content = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>{nome}</title>
</head>
<body>
  <main>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <p><a href="{site}" rel="noopener noreferrer nofollow" target="_blank">{site}</a></p>
  </main>
</body>
</html>"""
    return HTMLResponse(content=content, status_code=200)