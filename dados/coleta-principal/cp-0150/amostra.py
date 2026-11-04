import html
import uuid
from typing import Dict
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI()

perfis: Dict[str, dict] = {}


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError(
                "O site deve ser uma URL absoluta válida com esquema http ou https."
            )
        return v


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    if id not in perfis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado"
        )

    dados = perfis[id]
    nome_escaped = html.escape(dados["nome"], quote=True)
    bio_escaped = html.escape(dados["bio"], quote=True)
    site_escaped = html.escape(dados["site"], quote=True)

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Perfil de {nome_escaped}</title>
</head>
<body>
    <h1>{nome_escaped}</h1>
    <p>{bio_escaped}</p>
    <p><a href="{site_escaped}">Website</a></p>
</body>
</html>"""

    headers = {
        "Content-Security-Policy": "default-src 'none'; style-src 'self' 'unsafe-inline';",
        "X-Content-Type-Options": "nosniff",
    }

    return HTMLResponse(content=html_content, status_code=200, headers=headers)