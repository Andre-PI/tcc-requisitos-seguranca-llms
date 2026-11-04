import html
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

perfis: dict[str, dict] = {}


class PerfilCreate(BaseModel):
    nome: str
    bio: str
    site: str


@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilCreate):
    novo_id = str(uuid.uuid4())
    perfis[novo_id] = perfil.model_dump()
    return {"id": novo_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    if id not in perfis:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    perfil = perfis[id]
    nome = html.escape(perfil["nome"])
    bio = html.escape(perfil["bio"])
    site = html.escape(perfil["site"], quote=True)

    conteudo_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Perfil de {nome}</title>
</head>
<body>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <a href="{site}">Site</a>
</body>
</html>"""

    return HTMLResponse(content=conteudo_html, status_code=200)