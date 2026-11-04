from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
from html import escape
from typing import Dict

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: str

class PerfilOut(BaseModel):
    id: int

class Perfil:
    def __init__(self, nome: str, bio: str, site: str):
        self.nome = nome
        self.bio = bio
        self.site = site

_perfis: Dict[int, Perfil] = {}
_next_id = 1

@app.post("/perfil", status_code=status.HTTP_201_CREATED, response_model=PerfilOut)
def criar_perfil(perfil: PerfilIn):
    global _next_id
    pid = _next_id
    _next_id += 1
    _perfis[pid] = Perfil(perfil.nome, perfil.bio, perfil.site)
    return {"id": pid}

@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: int):
    perfil = _perfis.get(id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    nome = escape(perfil.nome, quote=False)
    bio = escape(perfil.bio, quote=False)
    site = escape(perfil.site, quote=True)

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
    return HTMLResponse(content=html, status_code=200)