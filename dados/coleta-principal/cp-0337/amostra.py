import html
import uuid
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator

app = FastAPI()

perfis = {}


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., min_length=1, max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlsplit(v)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError("O site deve ser uma URL absoluta http ou https.")
        return v


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(dados: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = dados.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}")
def obter_perfil(id: str):
    perfil = perfis.get(id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

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
    <p><a href="{site_escaped}">Website</a></p>
</body>
</html>"""

    headers = {
        "Content-Security-Policy": "default-src 'none'; style-src 'self' 'unsafe-inline';",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=html_content, media_type="text/html; charset=utf-8", headers=headers)