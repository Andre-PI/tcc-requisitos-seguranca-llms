import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
import jinja2

app = FastAPI()

perfis = {}

template_html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{{ nome }}</title>
</head>
<body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}">Website</a></p>
</body>
</html>
"""

env = jinja2.Environment(autoescape=True)
template = env.from_string(template_html)


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL inválida. Somente URLs absolutas http ou https são permitidas.")
        return v


@app.post("/perfil", status_code=201)
def criar_perfil(dados: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = {
        "nome": dados.nome,
        "bio": dados.bio,
        "site": dados.site,
    }
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: str):
    if perfil_id not in perfis:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    perfil = perfis[perfil_id]
    html_content = template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )

    headers = {
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline';",
        "X-Content-Type-Options": "nosniff",
    }

    return HTMLResponse(content=html_content, status_code=200, headers=headers)