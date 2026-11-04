import html
import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from jinja2 import Environment

app = FastAPI()

perfis: dict[str, dict[str, str]] = {}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Perfil de {{ nome }}</title>
</head>
<body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}" rel="noopener noreferrer">Website</a></p>
</body>
</html>"""

jinja_env = Environment(autoescape=True)
template = jinja_env.from_string(HTML_TEMPLATE)


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=500)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_site_url(cls, v: str) -> str:
        parsed = urlparse(v.strip())
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL inválida. Apenas esquemas http e https são permitidos.")
        return v.strip()


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(dados: PerfilCreate):
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

    conteudo_html = template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )
    return HTMLResponse(content=conteudo_html, status_code=status.HTTP_200_OK)