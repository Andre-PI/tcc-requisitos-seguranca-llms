import html
import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from jinja2 import Environment

app = FastAPI()

perfis = {}

jinja_env = Environment(autoescape=True)

TEMPLATE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Perfil de {{ nome }}</title>
</head>
<body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}">Site Pessoal</a></p>
</body>
</html>"""

template = jinja_env.from_string(TEMPLATE_HTML)


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL do site deve ser absoluta e usar esquema http ou https.")
        return v


@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}")
def obter_perfil(id: str):
    if id not in perfis:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    dados = perfis[id]
    conteudo_html = template.render(
        nome=dados["nome"],
        bio=dados["bio"],
        site=dados["site"],
    )

    headers = {
        "Content-Security-Policy": "default-src 'none'; script-src 'none';",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=conteudo_html, media_type="text/html; charset=utf-8", headers=headers)