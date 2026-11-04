from __future__ import annotations

from html import escape
from typing import Dict
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

app = FastAPI(title="Perfil Público")


def _strip_and_limit(value: str, max_length: int) -> str:
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"must be at most {max_length} characters")
    return value


NomeStr = Annotated[str, AfterValidator(lambda v: _strip_and_limit(v, 120))]
BioStr = Annotated[str, AfterValidator(lambda v: _strip_and_limit(v, 2000))]


class PerfilCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: NomeStr = Field(..., min_length=1)
    bio: BioStr = Field(..., min_length=1)
    site: HttpUrl

    @field_validator("site")
    @classmethod
    def validate_site_scheme(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("site must use http or https")
        return v

    @field_validator("nome", "bio")
    @classmethod
    def validate_no_control_chars(cls, v: str) -> str:
        if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in v):
            raise ValueError("contains invalid control characters")
        return v


class PerfilRecord(BaseModel):
    nome: str
    bio: str
    site: str


_store: Dict[int, PerfilRecord] = {}
_next_id = 1


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
async def criar_perfil(payload: PerfilCreate):
    global _next_id
    perfil_id = _next_id
    _next_id += 1

    _store[perfil_id] = PerfilRecord(
        nome=payload.nome,
        bio=payload.bio,
        site=str(payload.site),
    )
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"id": perfil_id})


@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
async def obter_perfil(perfil_id: int, request: Request):
    perfil = _store.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    nome = escape(perfil.nome, quote=True)
    bio = escape(perfil.bio, quote=True)
    site = escape(perfil.site, quote=True)

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Perfil público</title>
</head>
<body>
  <main>
    <h1>{nome}</h1>
    <p>{bio}</p>
    <p><a href="{site}" rel="noopener noreferrer nofollow" target="_blank">Site pessoal</a></p>
  </main>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)