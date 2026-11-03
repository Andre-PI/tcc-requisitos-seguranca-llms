from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Dict
from jinja2 import Environment, select_autoescape

app = FastAPI()

class PerfilCreate(BaseModel):
    nome: str
    bio: str
    site: HttpUrl

# armazenamento simples em memória
db: Dict[int, PerfilCreate] = {}
next_id = 1

jinja_env = Environment(
    autoescape=select_autoescape(enabled_extensions=('html', 'xml'), default_for_string=True)
)
template_html = jinja_env.from_string(
    """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8"/>
    <title>Perfil de {{ nome }}</title>
</head>
<body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}" target="_blank" rel="noopener noreferrer">Site pessoal</a></p>
</body>
</html>"""
)

@app.post("/perfil", status_code=status.HTTP_201_CREATED)
async def criar_perfil(perfil: PerfilCreate):
    global next_id
    # Validação já feita pelo Pydantic, incluindo URL e strings
    perfil_id = next_id
    next_id += 1
    db[perfil_id] = perfil
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"id": perfil_id})

@app.get("/perfil/{id}", response_class=HTMLResponse)
async def obter_perfil(id: int, request: Request):
    perfil = db.get(id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    content = template_html.render(nome=perfil.nome, bio=perfil.bio, site=perfil.site)
    return HTMLResponse(content=content, status_code=200)