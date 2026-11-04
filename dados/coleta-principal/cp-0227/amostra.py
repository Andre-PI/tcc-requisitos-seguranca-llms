from uuid import uuid4
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from jinja2 import Template
from pydantic import BaseModel

app = FastAPI()

perfis: dict[str, dict] = {}

template_html = Template("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Perfil de {{ perfil.nome }}</title>
</head>
<body>
    <h1>{{ perfil.nome }}</h1>
    <p>{{ perfil.bio }}</p>
    <a href="{{ perfil.site }}">{{ perfil.site }}</a>
</body>
</html>""")


class PerfilInput(BaseModel):
    nome: str
    bio: str
    site: str


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(dados: PerfilInput):
    perfil_id = str(uuid4())
    perfis[perfil_id] = dados.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: str):
    perfil = perfis.get(perfil_id)
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado"
        )
    html_content = template_html.render(perfil=perfil)
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)