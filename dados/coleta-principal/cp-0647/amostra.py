from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict
from html import escape
from itertools import count

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str = Field(min_length=1)
    bio: str = Field(min_length=1)
    site: HttpUrl

class PerfilOut(BaseModel):
    id: int

_perfis: Dict[int, PerfilIn] = {}
_next_id = count(1)

@app.post("/perfil", status_code=201, response_model=PerfilOut)
def criar_perfil(perfil: PerfilIn):
    perfil_id = next(_next_id)
    _perfis[perfil_id] = perfil
    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}")
def exibir_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    nome = escape(perfil.nome)
    bio = escape(perfil.bio)
    site = escape(str(perfil.site))

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>{nome}</title>
</head>
<body>
  <h1>{nome}</h1>
  <p>{bio}</p>
  <a href="{site}">{site}</a>
</body>
</html>"""
    return Response(content=html, media_type="text/html")