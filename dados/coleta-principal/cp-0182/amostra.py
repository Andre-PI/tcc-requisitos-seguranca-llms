from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
from jinja2 import Environment, select_autoescape
from html import escape

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: str

class PerfilOut(BaseModel):
    id: int

_perfis: dict[int, dict[str, str]] = {}
_next_id = 1

_jinja_env = Environment(autoescape=select_autoescape(enabled_extensions=("html", "htm", "xml"), default_for_string=True, default=True))
_template = _jinja_env.from_string(
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

@app.post("/perfil", status_code=201, response_model=PerfilOut)
def criar_perfil(perfil: PerfilIn):
    global _next_id
    pid = _next_id
    _next_id += 1
    _perfis[pid] = {
        "nome": perfil.nome,
        "bio": perfil.bio,
        "site": perfil.site,
    }
    return {"id": pid}

@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: int):
    perfil = _perfis.get(id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    html = _template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )
    return HTMLResponse(content=html, status_code=200)