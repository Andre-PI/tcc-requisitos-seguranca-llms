from uuid import uuid4
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from jinja2 import Template
from pydantic import BaseModel

app = FastAPI()

perfis: dict[str, dict] = {}

template_perfil = Template("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Perfil de {{ nome }}</title>
</head>
<body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}">Site</a></p>
</body>
</html>""")


class PerfilInput(BaseModel):
    nome: str
    bio: str
    site: str


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil: PerfilInput):
    perfil_id = str(uuid4())
    perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    perfil = perfis.get(id)
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado"
        )
    html_content = template_perfil.render(
        nome=perfil["nome"], bio=perfil["bio"], site=perfil["site"]
    )
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)