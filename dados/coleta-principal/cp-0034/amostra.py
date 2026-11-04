from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator
from typing import Dict
from html import escape as html_escape
from markupsafe import Markup
from jinja2 import Environment, select_autoescape
from urllib.parse import urlparse
import itertools
import re

app = FastAPI()

jinja_env = Environment(autoescape=select_autoescape(enabled_extensions=("html", "xml"), default=True))
template = jinja_env.from_string(
    """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Perfil público</title>
</head>
<body>
  <main>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}">Site pessoal</a></p>
  </main>
</body>
</html>"""
)

_id_counter = itertools.count(1)
_profiles: Dict[int, dict] = {}

def _validate_absolute_http_https_url(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("site inválido")
    if len(value) > 2048:
        raise ValueError("site muito longo")
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("site deve usar http ou https")
    if not parsed.netloc:
        raise ValueError("site inválido")
    return value

class PerfilCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    bio: str = Field(max_length=1000)
    site: str = Field(max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_site(cls, v: str) -> str:
        return _validate_absolute_http_https_url(v)

@app.post("/perfil", status_code=201)
async def criar_perfil(payload: PerfilCreate):
    perfil_id = next(_id_counter)
    _profiles[perfil_id] = {
        "nome": payload.nome,
        "bio": payload.bio,
        "site": payload.site,
    }
    return JSONResponse(status_code=201, content={"id": perfil_id})

@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
async def obter_perfil(perfil_id: int):
    perfil = _profiles.get(perfil_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    html = template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )
    headers = {
        "Content-Security-Policy": "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        "X-Content-Type-Options": "nosniff",
    }
    return HTMLResponse(content=html, status_code=200, headers=headers)