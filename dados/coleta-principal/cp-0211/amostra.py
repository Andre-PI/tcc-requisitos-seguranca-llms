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
    <title>{{ nome }}</title>
</head>
<body>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}" rel="noopener noreferrer">Website</a></p>
</body>
</html>""")

db: dict[str, dict] = {}


class PerfilCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=150)
    bio: str = Field(..., max_length=2000)
    site: str = Field(..., max_length=2048)

    @field_validator("site")
    @classmethod
    def validate_url(cls, v: str) -> str:
        parsed = urlparse(v.strip())
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL inválida. Apenas esquemas http e https são permitidos.")
        return v.strip()


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil: PerfilCreate):
    perfil_id = str(uuid.uuid4())
    db[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}


@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: str):
    perfil = db.get(id)
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    content = HTML_TEMPLATE.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"]
    )
    return HTMLResponse(content=content, status_code=status.HTTP_200_OK)