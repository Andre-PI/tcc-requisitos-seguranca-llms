from __future__ import annotations

from html import escape
from typing import Dict
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator

app = FastAPI(title="Perfil Público")


class PerfilCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    bio: str = Field(min_length=1, max_length=2000)
    site: HttpUrl

    @field_validator("nome", "bio")
    @classmethod
    def no_control_chars(cls, v: str) -> str:
        if any(ord(ch) < 32 for ch in v):
            raise ValueError("Caracteres de controle não são permitidos")
        return v

    @field_validator("site")
    @classmethod
    def validate_site_scheme(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("URL deve usar http ou https")
        return v


class PerfilStored(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str
    bio: str
    site: str


_db: Dict[int, PerfilStored] = {}
_next_id = 1


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(payload: PerfilCreate):
    global _next_id
    perfil_id = _next_id
    _next_id += 1

    _db[perfil_id] = PerfilStored(
        nome=payload.nome,
        bio=payload.bio,
        site=str(payload.site),
    )
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: int):
    perfil = _db.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    nome = escape(perfil.nome, quote=False)
    bio = escape(perfil.bio, quote=False)
    site_href = escape(perfil.site, quote=True)

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
    <p><a href="{site_href}" rel="noopener noreferrer nofollow" target="_blank">Site pessoal</a></p>
  </main>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)