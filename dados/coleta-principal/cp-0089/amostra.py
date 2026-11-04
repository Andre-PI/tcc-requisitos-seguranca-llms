import html
import uuid
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

perfis: Dict[str, dict] = {}


class PerfilCreate(BaseModel):
    nome: str
    bio: str
    site: str


@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: str):
    perfil = perfis.get(perfil_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    nome = html.escape(perfil["nome"])
    bio = html.escape(perfil["bio"])
    site = html.escape(perfil["site"], quote=True)

    conteudo_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{nome}</title>
</head>
<body>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <p><a href="{site}">Site</a></p>
</body>
</html>"""

    return HTMLResponse(content=conteudo_html, status_code=200)