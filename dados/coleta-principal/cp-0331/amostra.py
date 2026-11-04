from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, HttpUrl
from jinja2 import Template
from typing import Dict
from uuid import uuid4

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str
    bio: str
    site: HttpUrl

class PerfilOut(BaseModel):
    id: str

_perfis: Dict[str, dict] = {}

@app.post("/perfil", status_code=201, response_model=PerfilOut)
def criar_perfil(perfil: PerfilIn):
    perfil_id = str(uuid4())
    _perfis[perfil_id] = perfil.model_dump()
    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}")
def exibir_perfil(perfil_id: str):
    perfil = _perfis.get(perfil_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    html = Template(
        """
        <!doctype html>
        <html lang="pt-br">
          <head>
            <meta charset="utf-8">
            <title>Perfil público</title>
          </head>
          <body>
            <h1>{{ nome }}</h1>
            <p>{{ bio }}</p>
            <a href="{{ site }}">{{ site }}</a>
          </body>
        </html>
        """
    ).render(**perfil)

    return Response(content=html, media_type="text/html")