import html
import uuid
from typing import Dict
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

profiles_db: Dict[str, dict] = {}


class PerfilCreate(BaseModel):
    nome: str
    bio: str
    site: str


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    profiles_db[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: str):
    perfil = profiles_db.get(perfil_id)
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado"
        )

    nome_escaped = html.escape(perfil["nome"], quote=True)
    bio_escaped = html.escape(perfil["bio"], quote=True)
    site_escaped = html.escape(perfil["site"], quote=True)

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{nome_escaped}</title>
</head>
<body>
    <h1>{nome_escaped}</h1>
    <p>{bio_escaped}</p>
    <p><a href="{site_escaped}">{site_escaped}</a></p>
</body>
</html>"""

    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)