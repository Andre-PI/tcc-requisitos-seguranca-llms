from __future__ import annotations

from html import escape
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator
from pydantic import TypeAdapter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


app = FastAPI(title="Perfil Público", version="1.0.0")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        return response


app.add_middleware(SecurityHeadersMiddleware)


class PerfilIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    bio: str = Field(min_length=1, max_length=2000)
    site: str = Field(min_length=1, max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("site must use http or https")
        if not parsed.netloc:
            raise ValueError("site must include a host")
        if any(c in v for c in ("\x00", "\r", "\n")):
            raise ValueError("invalid characters in site")
        return v


class PerfilOut(BaseModel):
    id: int


_perfis: dict[int, dict[str, str]] = {}
_next_id: int = 1


@app.post("/perfil", status_code=status.HTTP_201_CREATED, response_model=PerfilOut)
async def criar_perfil(payload: PerfilIn) -> JSONResponse:
    global _next_id
    perfil_id = _next_id
    _next_id += 1
    _perfis[perfil_id] = {
        "nome": payload.nome,
        "bio": payload.bio,
        "site": payload.site,
    }
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"id": perfil_id})


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
async def obter_perfil(perfil_id: int) -> HTMLResponse:
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    nome = escape(perfil["nome"], quote=True)
    bio = escape(perfil["bio"], quote=True)
    site = escape(perfil["site"], quote=True)

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{nome}</title>
</head>
<body>
  <main>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <p><a href="{site}" rel="noopener noreferrer nofollow" target="_blank">Site pessoal</a></p>
  </main>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)