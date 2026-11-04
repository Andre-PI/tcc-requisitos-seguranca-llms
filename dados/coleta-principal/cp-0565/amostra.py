import html
import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from jinja2 import Environment

app = FastAPI()

perfis = {}

jinja_env = Environment(autoescape=True)
template = jinja_env.from_string("""<!DOCTYPE html>
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
</html>""")


class PerfilInput(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL deve ser absoluta com esquema http ou https.")
        return v


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(dados: PerfilInput):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = dados.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}")
def obter_perfil(id: str):
    if id not in perfis:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    perfil = perfis[id]
    html_content = template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"]
    )

    headers = {
        "Content-Security-Policy": "default-src 'self'; script-src 'none';",
        "X-Content-Type-Options": "nosniff"
    }

    return Response(content=html_content, media_type="text/html; charset=utf-8", headers=headers)