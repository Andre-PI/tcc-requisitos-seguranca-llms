from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, HttpUrl
from jinja2 import Environment, BaseLoader, select_autoescape

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: HttpUrl

_perfis: dict[int, dict[str, str]] = {}
_next_id = 1

_env = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(enabled_extensions=("html", "xml"), default_for_string=True),
)

_TEMPLATE = _env.from_string(
    """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Perfil público</title>
</head>
<body>
  <h1>{{ nome }}</h1>
  <p>{{ bio }}</p>
  <p><a href="{{ site }}">{{ site }}</a></p>
</body>
</html>"""
)

@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilIn):
    global _next_id
    perfil_id = _next_id
    _next_id += 1
    _perfis[perfil_id] = {
        "nome": perfil.nome,
        "bio": perfil.bio,
        "site": str(perfil.site),
    }
    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}")
def exibir_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    html = _TEMPLATE.render(**perfil)
    return Response(content=html, media_type="text/html")