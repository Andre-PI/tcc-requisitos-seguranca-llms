from __future__ import annotations

import html
import re
from dataclasses import dataclass
from threading import Lock
from typing import Annotated
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Path, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

app = FastAPI(title="Perfil Público", version="1.0.0")


class PerfilCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    nome: Annotated[str, Field(min_length=1, max_length=200)]
    bio: Annotated[str, Field(min_length=1, max_length=2000)]
    site: Annotated[str, Field(min_length=1, max_length=2048)]

    @field_validator("site")
    @classmethod
    def validar_site(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("site deve usar http ou https")
        if not parsed.netloc:
            raise ValueError("site inválido")
        if any(c in v for c in ("\x00", "\r", "\n")):
            raise ValueError("site inválido")
        return v


@dataclass(frozen=True, slots=True)
class Perfil:
    nome: str
    bio: str
    site: str


_perfis: dict[int, Perfil] = {}
_next_id = 1
_lock = Lock()


def _novo_id() -> int:
    global _next_id
    with _lock:
        perfil_id = _next_id
        _next_id += 1
        return perfil_id


def _salvar_perfil(perfil: Perfil) -> int:
    perfil_id = _novo_id()
    with _lock:
        _perfis[perfil_id] = perfil
    return perfil_id


def _obter_perfil(perfil_id: int) -> Perfil | None:
    with _lock:
        return _perfis.get(perfil_id)


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(payload: PerfilCreate):
    perfil = Perfil(nome=payload.nome, bio=payload.bio, site=payload.site)
    perfil_id = _salvar_perfil(perfil)
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(
    perfil_id: Annotated[int, Path(ge=1)],
):
    perfil = _obter_perfil(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    nome = html.escape(perfil.nome, quote=True)
    bio = html.escape(perfil.bio, quote=True)
    site_href = html.escape(perfil.site, quote=True)

    conteudo = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{nome}</title>
</head>
<body>
  <main>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <p><a href="{site_href}" rel="noopener noreferrer nofollow" target="_blank">Site pessoal</a></p>
  </main>
</body>
</html>"""
    return HTMLResponse(content=conteudo, status_code=status.HTTP_200_OK)