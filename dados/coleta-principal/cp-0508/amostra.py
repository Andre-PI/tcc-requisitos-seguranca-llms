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


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    if id not in profiles_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    perfil = profiles_db[id]
    nome = html.escape(perfil["nome"], quote=True)
    bio = html.escape(perfil["bio"], quote=True)
    site = html.escape(perfil["site"], quote=True)

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{nome}</title>
</head>
<body>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <a href="{site}">Website</a>
</body>
</html>"""

    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)