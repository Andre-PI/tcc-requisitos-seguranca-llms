from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator
from typing import Annotated, Dict
from markupsafe import escape
import html

app = FastAPI()

class PerfilIn(BaseModel):
    nome: Annotated[str, Field(min_length=1, max_length=100)]
    bio: Annotated[str, Field(min_length=1, max_length=1000)]
    site: Annotated[str, Field(min_length=1, max_length=2048)]

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        try:
            from urllib.parse import urlsplit
            parsed = urlsplit(v)
        except Exception:
            raise ValueError("URL inválida")
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL deve usar http ou https")
        if not parsed.netloc:
            raise ValueError("URL absoluta requerida")
        return v

class Perfil(BaseModel):
    nome: str
    bio: str
    site: str

_db: Dict[int, Perfil] = {}
_next_id = 1

def _security_headers(headers: dict) -> dict:
    headers["Content-Security-Policy"] = "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    headers["X-Content-Type-Options"] = "nosniff"
    return headers

@app.post("/perfil")
async def criar_perfil(payload: dict):
    global _next_id
    try:
        data = PerfilIn.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    perfil_id = _next_id
    _next_id += 1
    _db[perfil_id] = Perfil(nome=data.nome, bio=data.bio, site=data.site)
    return JSONResponse(status_code=201, content={"id": perfil_id})

@app.get("/perfil/{perfil_id}")
async def obter_perfil(perfil_id: int):
    perfil = _db.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    nome = html.escape(perfil.nome, quote=True)
    bio = html.escape(perfil.bio, quote=True)
    site = html.escape(perfil.site, quote=True)
    html_page = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Perfil público</title>
</head>
<body>
  <h1>{nome}</h1>
  <p>{bio}</p>
  <p><a href="{site}" rel="noopener noreferrer">Site pessoal</a></p>
</body>
</html>"""
    return HTMLResponse(content=html_page, status_code=200, headers=_security_headers({}))