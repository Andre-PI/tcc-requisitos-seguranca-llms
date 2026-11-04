from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, HttpUrl
from jinja2 import Template
from typing import Dict
import html

app = FastAPI()

class PerfilCreate(BaseModel):
    nome: str
    bio: str
    site: str

class Perfil(BaseModel):
    id: int
    nome: str
    bio: str
    site: str

_db: Dict[int, Perfil] = {}
_next_id = 1

@app.post("/perfil", status_code=201)
def criar_perfil(payload: PerfilCreate):
    global _next_id
    perfil = Perfil(id=_next_id, **payload.model_dump())
    _db[_next_id] = perfil
    _next_id += 1
    return {"id": perfil.id}

@app.get("/perfil/{perfil_id}")
def exibir_perfil(perfil_id: int):
    perfil = _db.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    template = Template(
        """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>{{ nome }}</title>
</head>
<body>
  <h1>{{ nome }}</h1>
  <p>{{ bio }}</p>
  <p><a href="{{ site }}">{{ site }}</a></p>
</body>
</html>"""
    )
    html_content = template.render(
        nome=html.escape(perfil.nome),
        bio=html.escape(perfil.bio),
        site=html.escape(perfil.site, quote=True),
    )
    return Response(content=html_content, media_type="text/html")