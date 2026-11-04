import html
import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from jinja2 import Environment, select_autoescape

app = FastAPI()

profiles_db: dict[str, dict[str, str]] = {}

jinja_env = Environment(autoescape=select_autoescape(["html", "xml"]))

PROFILE_TEMPLATE = jinja_env.from_string("""<!DOCTYPE html>
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
</html>
""")


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., min_length=1, max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_url(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError("O site deve conter esquema http ou https válido.")
        if not parsed.netloc:
            raise ValueError("O site deve conter um domínio válido.")
        return v


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil: PerfilCreate):
    profile_id = str(uuid.uuid4())
    profiles_db[profile_id] = perfil.model_dump()
    return {"id": profile_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    perfil = profiles_db.get(id)
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil não encontrado"
        )

    rendered_html = PROFILE_TEMPLATE.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"]
    )
    return HTMLResponse(content=rendered_html, status_code=status.HTTP_200_OK)