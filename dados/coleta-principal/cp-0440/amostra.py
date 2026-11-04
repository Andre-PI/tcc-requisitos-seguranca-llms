from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Dict
from uuid import uuid4
from urllib.parse import urlparse
from jinja2 import Environment, select_autoescape
import html

app = FastAPI()

env = Environment(autoescape=select_autoescape(enabled_extensions=("html", "htm", "xml"), default_for_string=True, default=True))

perfil_template = env.from_string(
    """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'">
  <meta http-equiv="X-Content-Type-Options" content="nosniff">
  <title>{{ nome }}</title>
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
        if parsed.scheme not in ("http", "https"):
            raise ValueError("site deve ser uma URL absoluta http ou https")
        if not parsed.netloc:
            raise ValueError("site deve ser uma URL absoluta http ou https")
        return v

class PerfilOut(BaseModel):
    id: str

_perfis: Dict[str, Dict[str, str]] = {}

@app.post("/perfil", status_code=201, response_model=PerfilOut)
async def criar_perfil(perfil: PerfilIn):
    pid = str(uuid4())
    _perfis[pid] = {"nome": perfil.nome, "bio": perfil.bio, "site": perfil.site}
    return {"id": pid}

@app.get("/perfil/{id}", response_class=HTMLResponse)
async def obter_perfil(id: str):
    perfil = _perfis.get(id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    html_body = perfil_template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )
    return HTMLResponse(
        content=html_body,
        status_code=200,
        headers={
            "Content-Security-Policy": "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
        },
        media_type="text/html; charset=utf-8",
    )