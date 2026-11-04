import html
import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
import jinja2

app = FastAPI()

profiles_db: dict[str, dict[str, str]] = {}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{{ nome }}</title>
</head>
<body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}">Site Pessoal</a></p>
</body>
</html>
"""

jinja_env = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    autoescape=jinja2.select_autoescape(["html", "xml"])
)
template = jinja_env.from_string(HTML_TEMPLATE)


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_site_url(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL inválida. Apenas esquemas http e https são permitidos.")
        return v


@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    profiles_db[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: str):
    perfil = profiles_db.get(perfil_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    rendered_html = template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"]
    )
    return HTMLResponse(content=rendered_html, status_code=200)