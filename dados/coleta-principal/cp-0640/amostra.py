from __future__ import annotations

from html import escape as html_escape
from typing import Dict
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Path, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator, model_validator
from pydantic import ConfigDict


app = FastAPI(title="Perfil Público")


class PerfilCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    bio: str = Field(min_length=1, max_length=5000)
    site: HttpUrl

    @field_validator("nome", "bio")
    @classmethod
    def no_control_chars(cls, v: str) -> str:
        if any(ch in v for ch in ("\x00", "\r")):
            raise ValueError("invalid characters")
        return v

    @model_validator(mode="after")
    def validate_site_scheme(self):
        scheme = self.site.scheme.lower()
        if scheme not in {"http", "https"}:
            raise ValueError("site must use http or https")
        return self


class PerfilStored(BaseModel):
    id: int
    nome: str
    bio: str
    site: str


_perfis: Dict[int, PerfilStored] = {}
_next_id = 1


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
async def criar_perfil(payload: PerfilCreate):
    global _next_id
    perfil_id = _next_id
    _next_id += 1

    _perfis[perfil_id] = PerfilStored(
        id=perfil_id,
        nome=payload.nome,
        bio=payload.bio,
        site=str(payload.site),
    )
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
async def obter_perfil(
    perfil_id: int = Path(..., ge=1),
):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    nome = html_escape(perfil.nome, quote=True)
    bio = html_escape(perfil.bio, quote=True)
    site = html_escape(perfil.site, quote=True)

    html = f"""<!DOCTYPE html>
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
    <p><a href="{site}" rel="noopener noreferrer nofollow" target="_blank">{site}</a></p>
  </main>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)