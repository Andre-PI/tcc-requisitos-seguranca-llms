from __future__ import annotations

import html
import re
import secrets
from dataclasses import dataclass
from typing import Dict
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Path, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints
from typing_extensions import Annotated


app = FastAPI()


NomeStr = Annotated[str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)]
BioStr = Annotated[str, StringConstraints(min_length=1, max_length=2000, strip_whitespace=True)]


class PerfilCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: NomeStr
    bio: BioStr
    site: HttpUrl


@dataclass(frozen=True)
class Perfil:
    nome: str
    bio: str
    site: str


_perfis: Dict[str, Perfil] = {}
_id_re = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def _novo_id() -> str:
    return secrets.token_urlsafe(16)


def _validar_id(perfil_id: str) -> str:
    if not _id_re.fullmatch(perfil_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil nao encontrado")
    return perfil_id


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def criar_perfil(payload: PerfilCreate) -> dict[str, str]:
    perfil_id = _novo_id()
    _perfis[perfil_id] = Perfil(
        nome=payload.nome,
        bio=payload.bio,
        site=str(payload.site),
    )
    return {"id": perfil_id}


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
def obter_perfil(perfil_id: str = Path(..., min_length=1, max_length=128)) -> HTMLResponse:
    perfil_id = _validar_id(perfil_id)
    perfil = _perfis.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil nao encontrado")

    nome = html.escape(perfil.nome, quote=False)
    bio = html.escape(perfil.bio, quote=False)
    site_href = html.escape(perfil.site, quote=True)

    html_body = (
        "<!doctype html>"
        '<html lang="pt-BR">'
        "<head>"
        '<meta charset="utf-8">'
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Perfil público</title>"
        "</head>"
        "<body>"
        f"<h1>{nome}</h1>"
        f"<p>{bio}</p>"
        f'<p><a href="{site_href}" rel="noopener noreferrer nofollow" target="_blank">Site pessoal</a></p>'
        "</body>"
        "</html>"
    )
    return HTMLResponse(content=html_body, status_code=status.HTTP_200_OK)