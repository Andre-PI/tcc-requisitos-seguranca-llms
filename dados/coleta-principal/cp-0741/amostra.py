import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from jinja2 import Environment, select_autoescape

app = FastAPI()

jinja_env = Environment(autoescape=select_autoescape(["html", "xml"]))

HTML_TEMPLATE = jinja_env.from_string("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Perfil de {{ nome }}</title>
</head>
<body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}">Website</a></p>
</body>
</html>""")

perfis = {}


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("O site deve ser uma URL absoluta http ou https válida.")
        return v


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: str):
    perfil = perfis.get(perfil_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    html_content = HTML_TEMPLATE.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )

    headers = {
        "Content-Security-Policy": "default-src 'none'; style-src 'self' 'unsafe-inline';",
        "X-Content-Type-Options": "nosniff",
    }

    return HTMLResponse(content=html_content, status_code=200, headers=headers)