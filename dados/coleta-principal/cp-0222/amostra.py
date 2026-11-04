from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Dict
from urllib.parse import urlparse
from jinja2 import Environment, select_autoescape, StrictUndefined
from markupsafe import escape
import html
import re

app = FastAPI()

env = Environment(
    autoescape=select_autoescape(enabled_extensions=("html", "xml"), default=True),
    undefined=StrictUndefined,
)

template = env.from_string(
    """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Perfil público</title>
</head>
<body>
  <h1>{{ nome }}</h1>
  <p>{{ bio }}</p>
  <p><a href="{{ site }}">Site pessoal</a></p>
</body>
</html>"""
)

class PerfilCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    bio: str = Field(max_length=1000)
    site: str = Field(min_length=1, max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("site must be an absolute http or https URL")
        if not parsed.netloc:
            raise ValueError("site must be an absolute http or https URL")
        return v

    @field_validator("nome", "bio")
    @classmethod
    def preserve_text(cls, v: str) -> str:
        return v

db: Dict[int, dict] = {}
next_id = 1

@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(payload: PerfilCreate):
    global next_id
    perfil_id = next_id
    next_id += 1
    db[perfil_id] = {"nome": payload.nome, "bio": payload.bio, "site": payload.site}
    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: int):
    perfil = db.get(perfil_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    html_content = template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )

    response = HTMLResponse(content=html_content, status_code=200)
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response