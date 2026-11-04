import html
import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from jinja2 import Environment

app = FastAPI()

jinja_env = Environment(autoescape=True)

HTML_TEMPLATE = jinja_env.from_string("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{{ perfil.nome }}</title>
</head>
<body>
    <h1>{{ perfil.nome }}</h1>
    <p>{{ perfil.bio }}</p>
    <p><a href="{{ perfil.site }}">Site Pessoal</a></p>
</body>
</html>""")

perfis_db = {}


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=500)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_site_url(cls, v: str) -> str:
        parsed = urlparse(v.strip())
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL deve começar com http:// ou https:// e conter domínio válido")
        return v.strip()


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis_db[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    perfil = perfis_db.get(id)
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    content = HTML_TEMPLATE.render(perfil=perfil)
    return HTMLResponse(content=content, status_code=status.HTTP_200_OK)