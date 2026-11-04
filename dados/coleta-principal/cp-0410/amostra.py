from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, HttpUrl
from jinja2 import Template
from typing import Dict
from html import escape

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: HttpUrl

class PerfilOut(BaseModel):
    id: int

_perfis: Dict[int, dict] = {}
_next_id = 1

@app.post("/perfil", status_code=201, response_model=PerfilOut)
def criar_perfil(perfil: PerfilIn):
    global _next_id
    pid = _next_id
    _next_id += 1
    _perfis[pid] = perfil.model_dump()
    return {"id": pid}

@app.get("/perfil/{perfil_id}")
def exibir_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    html = Template(
        """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Perfil Público</title>
</head>
<body>
  <h1>{{ nome }}</h1>
  <p>{{ bio }}</p>
  <p><a href="{{ site }}">{{ site }}</a></p>
</body>
</html>"""
    ).render(
        nome=escape(perfil["nome"]),
        bio=escape(perfil["bio"]),
        site=escape(str(perfil["site"])),
    )
    return Response(content=html, media_type="text/html")