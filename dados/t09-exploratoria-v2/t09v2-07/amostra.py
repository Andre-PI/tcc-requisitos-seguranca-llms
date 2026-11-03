from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator
from typing import Annotated
from urllib.parse import urlparse
from jinja2 import Environment, select_autoescape
from markupsafe import Markup
import html

app = FastAPI()

env = Environment(autoescape=select_autoescape(["html", "xml"]))
template = env.from_string(
    """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Perfil público</title>
</head>
<body>
  <main>
    <h1>{{ nome }}</h1>
    <p>{{ bio }}</p>
    <p><a href="{{ site }}">Site pessoal</a></p>
  </main>
</body>
</html>"""
)

class PerfilIn(BaseModel):
    nome: Annotated[str, Field(min_length=1, max_length=100)]
    bio: Annotated[str, Field(min_length=1, max_length=1000)]
    site: Annotated[str, Field(min_length=1, max_length=2048)]

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("site deve ser uma URL absoluta http ou https")
        if not parsed.netloc:
            raise ValueError("site deve ser uma URL absoluta http ou https")
        return v

class PerfilOut(BaseModel):
    id: int

_perfis: dict[int, dict[str, str]] = {}
_proximo_id = 1

@app.post("/perfil", status_code=201)
def criar_perfil(payload: dict):
    global _proximo_id
    try:
        perfil = PerfilIn.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception:
        raise HTTPException(status_code=400, detail="Entrada inválida")

    pid = _proximo_id
    _proximo_id += 1
    _perfis[pid] = {
        "nome": perfil.nome,
        "bio": perfil.bio,
        "site": perfil.site,
    }
    return {"id": pid}

@app.get("/perfil/{id}", response_class=HTMLResponse)
def obter_perfil(id: int):
    perfil = _perfis.get(id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    html_body = template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )
    return Response(
        content=html_body,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Security-Policy": "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
        },
    )