from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator
from typing import Dict
from html import escape
from jinja2 import Environment, select_autoescape
from urllib.parse import urlparse
from itertools import count
import re

app = FastAPI()

env = Environment(autoescape=select_autoescape(enabled_extensions=("html", "xml"), default=True))
template = env.from_string(
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

class PerfilIn(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    bio: str = Field(min_length=1, max_length=1000)
    site: str = Field(min_length=1, max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("site deve ser uma URL absoluta http ou https")
        if not parsed.netloc:
            raise ValueError("site deve ser uma URL absoluta http ou https")
        return v

class PerfilOut(BaseModel):
    id: int

_perfis: Dict[int, PerfilIn] = {}
_next_id = count(1)

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.post("/perfil", status_code=201)
async def criar_perfil(payload: dict):
    try:
        perfil = PerfilIn.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    perfil_id = next(_next_id)
    _perfis[perfil_id] = perfil
    return JSONResponse(status_code=201, content={"id": perfil_id})

@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
async def obter_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    html = template.render(
        nome=perfil.nome,
        bio=perfil.bio,
        site=perfil.site,
    )
    response = HTMLResponse(content=html, status_code=200)
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response