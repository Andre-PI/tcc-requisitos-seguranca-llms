import html
import uuid
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from jinja2 import Environment

app = FastAPI()

perfis = {}

jinja_env = Environment(autoescape=True)
HTML_TEMPLATE = jinja_env.from_string("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{{ nome }}</title>
</head>
<body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}" rel="noopener noreferrer">Website</a></p>
</body>
</html>""")


class PerfilInput(BaseModel):
    nome: str = Field(..., min_length=1, max_length=150)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        url_strip = v.strip()
        parsed = urlsplit(url_strip)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL inválida. Apenas protocolos HTTP e HTTPS são permitidos.")
        return url_strip


class PerfilOutput(BaseModel):
    id: str


@app.post("/perfil", status_code=status.HTTP_201_CREATED, response_model=PerfilOutput)
def criar_perfil(dados: PerfilInput):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = {
        "nome": dados.nome,
        "bio": dados.bio,
        "site": dados.site,
    }
    return {"id": perfil_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    perfil = perfis.get(id)
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    conteudo_html = HTML_TEMPLATE.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )
    return HTMLResponse(content=conteudo_html, status_code=200)