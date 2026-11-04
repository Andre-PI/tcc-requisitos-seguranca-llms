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


class PerfilResponse(BaseModel):
    id: str


@app.post("/perfil", status_code=status.HTTP_201_CREATED, response_model=PerfilResponse)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    if id not in perfis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    perfil = perfis[id]
    nome_escaped = html.escape(perfil["nome"])
    bio_escaped = html.escape(perfil["bio"])
    site_escaped = html.escape(perfil["site"])

    conteudo_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{nome_escaped}</title>
</head>
<body>
    <h1>{nome_escaped}</h1>
    <p>{bio_escaped}</p>
    <a href="{site_escaped}">Site</a>
</body>
</html>"""

    return HTMLResponse(content=conteudo_html, status_code=status.HTTP_200_OK)