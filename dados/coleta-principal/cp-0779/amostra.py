from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict
from html import escape
from itertools import count

app = FastAPI()

class PerfilIn(BaseModel):
    nome: str = Field(min_length=1)
    bio: str = Field(min_length=1)
    site: HttpUrl

_perfis: Dict[int, PerfilIn] = {}
_id_seq = count(1)

@app.post("/perfil", status_code=201)
def criar_perfil(perfil: PerfilIn):
    perfil_id = next(_id_seq)
    _perfis[perfil_id] = perfil
    return {"id": perfil_id}

@app.get("/perfil/{perfil_id}")
def exibir_perfil(perfil_id: int):
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Perfil Público</title>
</head>
<body>
  <h1>{escape(perfil.nome)}</h1>
  <p>{escape(perfil.bio)}</p>
  <a href="{escape(str(perfil.site), quote=True)}">{escape(str(perfil.site))}</a>
</body>
</html>"""
    return Response(content=html, media_type="text/html")