from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
from html import escape

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: str

class PerfilOut(BaseModel):
    id: int

_perfis: dict[int, dict[str, str]] = {}
_next_id = 1

@app.post("/perfil", status_code=status.HTTP_201_CREATED, response_model=PerfilOut)
def criar_perfil(perfil: PerfilIn):
    global _next_id
    perfil_id = _next_id
    _next_id += 1
    _perfis[perfil_id] = {
        "nome": perfil.nome,
        "bio": perfil.bio,
        "site": perfil.site,
    }
    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    nome = escape(perfil["nome"], quote=True)
    bio = escape(perfil["bio"], quote=True)
    site = escape(perfil["site"], quote=True)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>{nome}</title>
</head>
<body>
  <h1>{nome}</h1>
  <p>{bio}</p>
  <p><a href="{site}">{site}</a></p>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)