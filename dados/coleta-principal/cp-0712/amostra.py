from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse
from jinja2 import Environment, select_autoescape
from html import escape as html_escape
from itertools import count
import re

app = FastAPI()

env = Environment(
    autoescape=select_autoescape(enabled_extensions=("html", "xml"), default_for_string=True, default=True)
)

PROFILE_TEMPLATE = env.from_string(
    """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Perfil público</title>
</head>
<body>
  <main>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}" rel="noopener noreferrer nofollow">Site pessoal</a></p>
  </main>
</body>
</html>"""
)

profiles = {}
next_id = count(1)

class PerfilIn(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    bio: str = Field(min_length=1, max_length=1000)
    site: str = Field(min_length=1, max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("site must be an absolute http or https URL")
        if any(c in v for c in ("\x00", "\r", "\n")):
            raise ValueError("invalid characters in url")
        return v

def _render_profile(profile: dict) -> str:
    return PROFILE_TEMPLATE.render(
        nome=profile["nome"],
        bio=profile["bio"],
        site=profile["site"],
    )

@app.post("/perfil", status_code=201)
async def criar_perfil(payload: PerfilIn):
    pid = str(next(next_id))
    profiles[pid] = payload.model_dump()
    return JSONResponse(status_code=201, content={"id": pid})

@app.get("/perfil/{id}", response_class=HTMLResponse)
async def obter_perfil(id: str):
    profile = profiles.get(id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    html = _render_profile(profile)
    response = HTMLResponse(content=html, status_code=200)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    return response