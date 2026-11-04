import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
import jinja2

app = FastAPI()

perfis = {}

template_str = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{{ perfil.nome }}</title>
</head>
<body>
    <h1>{{ perfil.nome }}</h1>
    <p>{{ perfil.bio }}</p>
    <p><a href="{{ perfil.site }}">Website</a></p>
</body>
</html>"""

jinja_env = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    autoescape=jinja2.select_autoescape(["html", "xml"])
)
template = jinja_env.from_string(template_str)


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError("URL deve usar o esquema http ou https.")
        if not parsed.netloc:
            raise ValueError("URL inválida.")
        return v


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(dados: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = dados.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    if id not in perfis:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    perfil = perfis[id]
    html_content = template.render(perfil=perfil)

    headers = {
        "Content-Security-Policy": "default-src 'self'; script-src 'none';",
        "X-Content-Type-Options": "nosniff",
    }
    return HTMLResponse(content=html_content, status_code=200, headers=headers)