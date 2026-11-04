from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, HttpUrl
from html import escape
from typing import Dict, Any
from jinja2 import Environment, BaseLoader, select_autoescape

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: str

_perfis: Dict[int, Dict[str, Any]] = {}
_next_id = 1

_env = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(enabled_extensions=("html", "xml"), default=True),
)

_TEMPLATE = _env.from_string(
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

@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilIn):
    global _next_id
    perfil_id = _next_id
    _next_id += 1
    _perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}

@app.get("/perfil/{id}")
def obter_perfil(id: int):
    perfil = _perfis.get(id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    html = _TEMPLATE.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )
    return Response(content=html, media_type="text/html")