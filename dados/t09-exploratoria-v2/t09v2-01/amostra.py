from __future__ import annotations

from html import escape
from typing import Dict, Any
from uuid import uuid4
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


app = FastAPI(title="Perfil Público", version="1.0.0")


class PerfilCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    bio: str = Field(min_length=1, max_length=2000)
    site: HttpUrl

    @field_validator("nome", "bio")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("campo vazio")
        return v

    @field_validator("site")
    @classmethod
    def validate_site_scheme(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("scheme inválido")
        return v


class PerfilRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str
    bio: str
    site: str


_storage: Dict[str, PerfilRecord] = {}


def _safe_href(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL inválida")
    if not parsed.netloc:
        raise ValueError("URL inválida")
    return url


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
async def criar_perfil(payload: PerfilCreate, request: Request) -> JSONResponse:
    try:
        site = _safe_href(str(payload.site))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="URL inválida")

    perfil_id = uuid4().hex
    _storage[perfil_id] = PerfilRecord(nome=payload.nome, bio=payload.bio, site=site)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"id": perfil_id})


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
async def obter_perfil(perfil_id: str) -> HTMLResponse:
    perfil = _storage.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    nome = escape(perfil.nome, quote=True)
    bio = escape(perfil.bio, quote=True)
    site = escape(perfil.site, quote=True)

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
    <p><a href="{site}" rel="noopener noreferrer nofollow">Site pessoal</a></p>
  </main>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)