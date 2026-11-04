from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Dict
from html import escape as html_escape
from jinja2 import Environment, BaseLoader, select_autoescape
from urllib.parse import urlparse
import itertools

app = FastAPI()

env = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(enabled_extensions=("html", "xml"), default=True),
)

TEMPLATE = env.from_string(
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
        try:
            parsed = urlparse(v)
        except Exception:
            raise ValueError("URL inválida")
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("URL deve usar http ou https")
        if not parsed.netloc:
            raise ValueError("URL absoluta inválida")
        return v

class PerfilOut(BaseModel):
    id: int

_perfis: Dict[int, Dict[str, str]] = {}
_seq = itertools.count(1)

@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilIn):
    perfil_id = next(_seq)
    _perfis[perfil_id] = {
        "nome": perfil.nome,
        "bio": perfil.bio,
        "site": perfil.site,
    }
    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    html = TEMPLATE.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )
    return HTMLResponse(
        content=html,
        status_code=200,
        headers={
            "Content-Security-Policy": "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
        },
    )