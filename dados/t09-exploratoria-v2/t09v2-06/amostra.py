from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, HttpUrl
from typing import Dict
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from fastapi import status
import html

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: str

class Perfil:
    def __init__(self, nome: str, bio: str, site: str):
        self.nome = nome
        self.bio = bio
        self.site = site

_perfis: Dict[int, Perfil] = {}
_next_id = 1

@app.post("/perfil", status_code=status.HTTP_201_CREATED)
async def criar_perfil(perfil: PerfilIn):
    global _next_id
    # No validation for URL schema beyond string, as site is str
    # Store profile
    p = Perfil(perfil.nome, perfil.bio, perfil.site)
    perfil_id = _next_id
    _perfis[perfil_id] = p
    _next_id += 1
    return JSONResponse(status_code=201, content={"id": perfil_id})

@app.get("/perfil/{id}", response_class=HTMLResponse)
async def ler_perfil(id: int, request: Request):
    p = _perfis.get(id)
    if not p:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    # Escape nome and bio for safe HTML text content
    nome_esc = html.escape(p.nome)
    bio_esc = html.escape(p.bio)
    # site is used as href attribute, escape quotes and ampersands
    site_esc = html.escape(p.site, quote=True)
    content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Perfil {id}</title></head>
<body>
<h1>{nome_esc}</h1>
<p>{bio_esc}</p>
<p><a href="{site_esc}">Site pessoal</a></p>
</body>
</html>"""
    return HTMLResponse(content=content, status_code=200)