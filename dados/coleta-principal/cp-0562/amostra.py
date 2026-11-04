import html
import uuid
from typing import Dict
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl

app = FastAPI()

profiles_db: Dict[str, dict] = {}


class PerfilCreate(BaseModel):
    nome: str
    bio: str
    site: str


class PerfilResponse(BaseModel):
    id: str


@app.post("/perfil", status_code=status.HTTP_201_CREATED, response_model=PerfilResponse)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    profiles_db[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: str):
    if perfil_id not in profiles_db:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    dados = profiles_db[perfil_id]
    nome = html.escape(dados["nome"])
    bio = html.escape(dados["bio"])
    site = html.escape(dados["site"], quote=True)

    conteudo_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{nome}</title>
</head>
<body>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <p><a href="{site}">{site}</a></p>
</body>
</html>"""

    return HTMLResponse(content=conteudo_html, status_code=200)