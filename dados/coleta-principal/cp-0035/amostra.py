import uuid
import html
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

db = {}

class PerfilCreate(BaseModel):
    nome: str
    bio: str
    site: str

@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    db[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}

@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    if id not in db:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    
    perfil = db[id]
    nome_escaped = html.escape(perfil["nome"])
    bio_escaped = html.escape(perfil["bio"])
    site_escaped = html.escape(perfil["site"])

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{nome_escaped}</title>
</head>
<body>
    <h1>{nome_escaped}</h1>
    <p>{bio_escaped}</p>
    <p><a href="{site_escaped}">Website</a></p>
</body>
</html>"""
    return HTMLResponse(content=html_content, status_code=200)