from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, AnyUrl
from jinja2 import Template
from typing import Dict
from itertools import count

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: AnyUrl

class PerfilOut(BaseModel):
    id: int

_perfis: Dict[int, PerfilIn] = {}
_next_id = count(1)

@app.post("/perfil", status_code=status.HTTP_201_CREATED, response_model=PerfilOut)
def criar_perfil(payload: PerfilIn):
    perfil_id = next(_next_id)
    _perfis[perfil_id] = payload
    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}", response_class=Response)
def exibir_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    template = Template(
        """
<!doctype html>
<html lang="pt-br">
  <head>
    <meta charset="utf-8">
    <title>Perfil Público</title>
  </head>
  <body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <a href="{{ site }}">{{ site }}</a>
  </body>
</html>
"""
    )
    html = template.render(nome=perfil.nome, bio=perfil.bio, site=str(perfil.site))
    return Response(content=html, media_type="text/html")