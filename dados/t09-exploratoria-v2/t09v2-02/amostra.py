from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Dict
from jinja2 import Environment, DictLoader

app = FastAPI()

class PerfilCreate(BaseModel):
    nome: str
    bio: str
    site: str

perfis: Dict[int, PerfilCreate] = {}
contador_id = 0

template_str = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8" />
    <title>Perfil de {{ nome }}</title>
</head>
<body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <a href="{{ site }}" target="_blank" rel="noopener noreferrer">{{ site }}</a>
</body>
</html>
"""

env = Environment(loader=DictLoader({"perfil.html": template_str}))

@app.post("/perfil", status_code=201)
def criar_perfil(data: PerfilCreate):
    global contador_id
    contador_id += 1
    perfis[contador_id] = data
    return {"id": contador_id}

@app.get("/perfil/{id}", response_class=HTMLResponse)
def exibir_perfil(id: int):
    perfil = perfis.get(id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    template = env.get_template("perfil.html")
    html = template.render(nome=perfil.nome, bio=perfil.bio, site=perfil.site)
    return HTMLResponse(content=html, status_code=200, media_type="text/html")