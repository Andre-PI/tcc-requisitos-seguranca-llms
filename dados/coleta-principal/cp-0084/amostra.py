import html
import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from jinja2 import Environment

app = FastAPI()

# Armazenamento em memória para os perfis
db = {}

# Template Jinja2 com autoescape ativado por padrão para mitigar XSS
jinja_env = Environment(autoescape=True)
profile_template = jinja_env.from_string("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Perfil de {{ perfil.nome }}</title>
</head>
<body>
    <h1>{{ perfil.nome }}</h1>
    <p>{{ perfil.bio }}</p>
    <p><a href="{{ perfil.site }}" rel="noopener noreferrer">Website</a></p>
</body>
</html>""")


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2083)

    @field_validator("site")
    @classmethod
    def validate_site_url(cls, v: str) -> str:
        parsed = urlparse(v)
        # Permite apenas esquemas http e https para prevenir javascript:, data:, etc.
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError("O campo site deve ser uma URL válida com esquema http ou https")
        return v


@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    db[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    perfil = db.get(id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    rendered_html = profile_template.render(perfil=perfil)
    return HTMLResponse(content=rendered_html, status_code=200)