from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, HttpUrl
from jinja2 import Environment, BaseLoader, select_autoescape
from typing import Dict
from itertools import count
from html import escape

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: HttpUrl

_perfis: Dict[int, dict] = {}
_ids = count(1)

_env = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(["html", "xml"]),
)

_TEMPLATE = _env.from_string(
    """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Perfil Público</title>
</head>
<body>
  <h1>{{ nome }}</h1>
  <p>{{ bio }}</p>
  <p><a href="{{ site }}">Site</a></p>
</body>
</html>"""
)

@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilIn):
    perfil_id = next(_ids)
    _perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}")
def exibir_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    html = _TEMPLATE.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=str(perfil["site"]),
    )
    return Response(content=html, media_type="text/html")