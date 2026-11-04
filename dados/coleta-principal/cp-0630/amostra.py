from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Dict
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from jinja2 import Environment, BaseLoader, select_autoescape

app = FastAPI(title="Perfil Público", version="1.0.0")

env = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(enabled_extensions=("html", "xml"), default=True),
)

PROFILE_TEMPLATE = env.from_string(
    """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ nome }}</title>
</head>
<body>
  <main>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}" rel="noopener noreferrer nofollow" target="_blank">Site pessoal</a></p>
  </main>
</body>
</html>"""
)


class PerfilCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    bio: str = Field(min_length=1, max_length=5000)
    site: str = Field(min_length=1, max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("site deve usar http ou https")
        if not parsed.netloc:
            raise ValueError("site inválido")
        if any(c in v for c in ("\x00", "\r", "\n")):
            raise ValueError("site inválido")
        return v


@dataclass(frozen=True)
class Perfil:
    nome: str
    bio: str
    site: str


_perfis: Dict[int, Perfil] = {}
_next_id: int = 1


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
async def criar_perfil(payload: PerfilCreate):
    global _next_id
    perfil_id = _next_id
    _next_id += 1
    _perfis[perfil_id] = Perfil(nome=payload.nome, bio=payload.bio, site=payload.site)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"id": perfil_id})


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
async def obter_perfil(perfil_id: int, request: Request):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    html_text = PROFILE_TEMPLATE.render(
        nome=perfil.nome,
        bio=perfil.bio,
        site=perfil.site,
    )
    return HTMLResponse(content=html_text, status_code=status.HTTP_200_OK)