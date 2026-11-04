from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from urllib.parse import urlparse
from jinja2 import Environment, select_autoescape
import html
import re

app = FastAPI()

env = Environment(autoescape=select_autoescape(enabled_extensions=("html", "htm"), default=True))
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

profiles = {}
next_id = 1

MAX_NOME = 100
MAX_BIO = 1000
MAX_SITE = 2048


class PerfilIn(BaseModel):
    nome: str = Field(..., max_length=MAX_NOME)
    bio: str = Field(..., max_length=MAX_BIO)
    site: str = Field(..., max_length=MAX_SITE)

    @field_validator("nome", "bio", "site")
    @classmethod
    def must_be_string(cls, v):
        if not isinstance(v, str):
            raise ValueError("deve ser string")
        return v

    @field_validator("site")
    @classmethod
    def validate_site(cls, v):
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("site deve ser URL absoluta http ou https")
        if not parsed.netloc:
            raise ValueError("site deve ser URL absoluta http ou https")
        return v

    @model_validator(mode="after")
    def validate_lengths(self):
        if len(self.nome) > MAX_NOME or len(self.bio) > MAX_BIO or len(self.site) > MAX_SITE:
            raise ValueError("limite de tamanho excedido")
        return self


@app.post("/perfil", status_code=201)
async def criar_perfil(payload: PerfilIn):
    global next_id
    perfil_id = str(next_id)
    next_id += 1
    profiles[perfil_id] = {
        "nome": payload.nome,
        "bio": payload.bio,
        "site": payload.site,
    }
    return JSONResponse(status_code=201, content={"id": perfil_id})


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
async def obter_perfil(perfil_id: str):
    perfil = profiles.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    rendered = template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )
    response = HTMLResponse(content=rendered, status_code=200)
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response