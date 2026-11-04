from __future__ import annotations

from html import escape
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator


app = FastAPI()

_PROFILES: dict[int, dict[str, str]] = {}
_NEXT_ID = 1


class PerfilIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=100)
    bio: str = Field(min_length=1, max_length=1000)
    site: str = Field(min_length=1, max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("site must be an absolute http or https URL")
        if not parsed.netloc:
            raise ValueError("site must be an absolute http or https URL")
        return v


def _html_response(content: str, status_code: int = 200) -> HTMLResponse:
    resp = HTMLResponse(content=content, status_code=status_code)
    resp.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.post("/perfil")
async def criar_perfil(payload: PerfilIn) -> JSONResponse:
    global _NEXT_ID
    profile_id = _NEXT_ID
    _NEXT_ID += 1
    _PROFILES[profile_id] = {
        "nome": payload.nome,
        "bio": payload.bio,
        "site": payload.site,
    }
    return JSONResponse(status_code=201, content={"id": profile_id})


@app.get("/perfil/{profile_id}")
async def obter_perfil(profile_id: int) -> HTMLResponse:
    perfil = _PROFILES.get(profile_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    nome = escape(perfil["nome"], quote=True)
    bio = escape(perfil["bio"], quote=True)
    site = escape(perfil["site"], quote=True)

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Perfil público</title>
</head>
<body>
  <main>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <p><a href="{site}" rel="noopener noreferrer">Site pessoal</a></p>
  </main>
</body>
</html>"""
    return _html_response(html)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> HTMLResponse:
    if exc.status_code == 404:
        return _html_response("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>404</title></head><body><h1>404</h1></body></html>", 404)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})