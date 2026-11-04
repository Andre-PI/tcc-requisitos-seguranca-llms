from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
from html import escape
from typing import Dict

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: HttpUrl

class Perfil(BaseModel):
    id: int
    nome: str
    bio: str
    site: str

_perfis: Dict[int, Perfil] = {}
_next_id = 1

@app.post("/perfil", status_code=201)
def criar_perfil(payload: PerfilIn):
    global _next_id
    perfil = Perfil(
        id=_next_id,
        nome=payload.nome,
        bio=payload.bio,
        site=str(payload.site),
    )
    _perfis[_next_id] = perfil
    _next_id += 1
    return {"id": perfil.id}

@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: int):
    perfil = _perfis.get(id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>{escape(perfil.nome)}</title>
</head>
<body>
  <h1>{escape(perfil.nome)}</h1>
  <p>{escape(perfil.bio)}</p>
  <p><a href="{escape(perfil.site, quote=True)}">{escape(perfil.site)}</a></p>
</body>
</html>"""
    return Response(content=html, media_type="text/html")