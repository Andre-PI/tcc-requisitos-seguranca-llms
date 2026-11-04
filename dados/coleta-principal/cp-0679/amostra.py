from __future__ import annotations

from html import escape
from typing import Annotated
from uuid import uuid4
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Path, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator


app = FastAPI(title="Perfil Público")


class PerfilCreate(BaseModel):
    nome: Annotated[str, Field(min_length=1, max_length=200)]
    bio: Annotated[str, Field(min_length=1, max_length=2000)]
    site: HttpUrl

    @field_validator("nome", "bio")
    @classmethod
    def strip_and_validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("campo obrigatório")
        return v


_perfis: dict[str, PerfilCreate] = {}


def _safe_href(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("scheme inválido")
    if not parsed.netloc:
        raise ValueError("URL inválida")
    return url


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
async def criar_perfil(payload: dict) -> JSONResponse:
    try:
        perfil = PerfilCreate.model_validate(payload)
        site = _safe_href(str(perfil.site))
    except (ValidationError, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dados inválidos")

    perfil_id = uuid4().hex
    _perfis[perfil_id] = PerfilCreate(nome=perfil.nome, bio=perfil.bio, site=site)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"id": perfil_id})


@app.get("/perfil/{id}", response_class=HTMLResponse)
async def obter_perfil(id: Annotated[str, Path(min_length=1, max_length=64)]) -> HTMLResponse:
    perfil = _perfis.get(id)
    if perfil is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    nome = escape(perfil.nome, quote=True)
    bio = escape(perfil.bio, quote=True)
    site = escape(str(perfil.site), quote=True)

    html = f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8">
    <title>{nome}</title>
  </head>
  <body>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <p><a href="{site}" rel="noopener noreferrer nofollow">Site pessoal</a></p>
  </body>
</html>"""
    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)