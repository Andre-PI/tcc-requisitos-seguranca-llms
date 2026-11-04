import html
import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
from jinja2 import Environment

app = FastAPI()

profiles_db = {}

jinja_env = Environment(autoescape=True)

HTML_TEMPLATE = jinja_env.from_string("""<!DOCTYPE html>
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
    nome: str
    bio: str
    site: str

    @field_validator("nome", "bio")
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("O campo não pode ser vazio.")
        return v

    @field_validator("site")
    @classmethod
    def validate_url(cls, v: str) -> str:
        parsed = urlparse(v.strip())
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL inválida. Apenas esquemas http e https são permitidos.")
        return v.strip()


@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilCreate):
    profile_id = str(uuid.uuid4())
    profiles_db[profile_id] = perfil.model_dump()
    return {"id": profile_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    perfil = profiles_db.get(id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")

    content = HTML_TEMPLATE.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"]
    )
    return HTMLResponse(content=content, status_code=200)