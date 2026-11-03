from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, HttpUrl
from typing import Dict
import html
from jinja2 import Template

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: HttpUrl

class PerfilOut(BaseModel):
    id: int

_perfis: Dict[int, dict] = {}
_next_id = 1

@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilIn):
    global _next_id
    perfil_id = _next_id
    _next_id += 1
    _perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}", response_class=Response)
def exibir_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    template = Template(
        """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Perfil público</title>
</head>
<body>
  <h1>{{ nome }}</h1>
  <p>{{ bio }}</p>
  <p><a href="{{ site }}">Site</a></p>
</body>
</html>"""
    )

    html_content = template.render(
        nome=html.escape(perfil["nome"]),
        bio=html.escape(perfil["bio"]),
        site=html.escape(str(perfil["site"]))
    )
    return Response(content=html_content, media_type="text/html")