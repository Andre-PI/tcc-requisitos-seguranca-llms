import uuid
import html
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

perfis: dict[str, dict] = {}


class PerfilCreate(BaseModel):
    nome: str
    bio: str
    site: str


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    if id not in perfis:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    dados = perfis[id]
    nome_escapado = html.escape(dados["nome"])
    bio_escapada = html.escape(dados["bio"])
    site_escapado = html.escape(dados["site"], quote=True)

    conteudo_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{nome_escapado}</title>
</head>
<body>
    <h1>{nome_escapado}</h1>
    <p>{bio_escapada}</p>
    <p><a href="{site_escapado}">Site Pessoal</a></p>
</body>
</html>"""

    return HTMLResponse(content=conteudo_html, status_code=200)