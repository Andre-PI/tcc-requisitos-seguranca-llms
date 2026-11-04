import html
import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from jinja2 import Environment

app = FastAPI()

perfis: dict[str, dict[str, str]] = {}

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
    <p><a href="{{ site }}" rel="noopener noreferrer">Website</a></p>
</body>
</html>"""

template = jinja_env.from_string(TEMPLATE_HTML)


class PerfilInput(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=500)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("O site deve conter uma URL válida com esquema http ou https.")
        return v


class PerfilOutput(BaseModel):
    id: str


@app.post("/perfil", status_code=status.HTTP_201_CREATED, response_model=PerfilOutput)
def criar_perfil(dados: PerfilInput):
    perfil_id = str(uuid.uuid4())
    perfis[perfil_id] = dados.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: str):
    perfil = perfis.get(perfil_id)
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    conteudo = template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"]
    )
    return HTMLResponse(content=conteudo, status_code=status.HTTP_200_OK)