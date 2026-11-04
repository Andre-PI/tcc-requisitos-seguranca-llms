from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, AnyHttpUrl, ValidationError, field_validator
from typing import Dict
from urllib.parse import urlparse
from html import escape
from jinja2 import Environment, BaseLoader, select_autoescape
from threading import Lock

app = FastAPI()

env = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(enabled_extensions=("html", "htm", "xml"), default=True),
)

_TEMPLATE = env.from_string(
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

class PerfilCreate(BaseModel):
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

_perfis: Dict[int, dict] = {}
_next_id = 1
_lock = Lock()

@app.post("/perfil", status_code=201)
def criar_perfil(payload: dict):
    global _next_id
    try:
        data = PerfilCreate.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    with _lock:
        perfil_id = _next_id
        _next_id += 1
        _perfis[perfil_id] = {
            "nome": data.nome,
            "bio": data.bio,
            "site": data.site,
        }

    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    html = _TEMPLATE.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )

    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Security-Policy": "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
        },
        status_code=200,
    )