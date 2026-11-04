import html
import uuid
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl

app = FastAPI()

profiles: Dict[str, dict] = {}


class ProfileCreate(BaseModel):
    nome: str
    bio: str
    site: str


class ProfileResponse(BaseModel):
    id: str


@app.post("/perfil", status_code=201, response_model=ProfileResponse)
def create_profile(profile: ProfileCreate):
    profile_id = str(uuid.uuid4())
    profiles[profile_id] = {
        "nome": profile.nome,
        "bio": profile.bio,
        "site": profile.site,
    }
    return {"id": profile_id}


@app.get("/perfil/{profile_id}", response_class=HTMLResponse)
def get_profile(profile_id: str):
    profile = profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    nome = html.escape(profile["nome"], quote=True)
    bio = html.escape(profile["bio"], quote=True)
    site = html.escape(profile["site"], quote=True)

    content = f"""<!DOCTYPE html>
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

    return HTMLResponse(content=content, status_code=200)