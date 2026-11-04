import html
from urllib.parse import urlparse
import uuid
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI()

perfis: dict[str, dict] = {}


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_site_url(cls, v: str) -> str:
        parsed = urlparse(v.strip())
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError(
                "A URL deve utilizar esquema http ou https e possuir um domínio válido."
            )
        return v.strip()


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    perfil = perfis.get(id)
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
    <title>Perfil de {nome_escaped}</title>
</head>
<body>
    <h1>{nome_escaped}</h1>
    <p>{bio_escaped}</p>
    <p><a href="{site_escaped}">Site Pessoal</a></p>
</body>
</html>"""
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)