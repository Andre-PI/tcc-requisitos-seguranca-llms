import uuid
import html
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

perfis: dict[str, dict[str, str]] = {}


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
    perfil = perfis.get(id)
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    nome = html.escape(perfil["nome"], quote=True)
    bio = html.escape(perfil["bio"], quote=True)
    site = html.escape(perfil["site"], quote=True)

    conteudo = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Perfil de {nome}</title>
</head>
<body>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <p><a href="{site}">Site Pessoal</a></p>
</body>
</html>"""
    return HTMLResponse(content=conteudo, status_code=status.HTTP_200_OK)