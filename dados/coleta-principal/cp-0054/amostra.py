from __future__ import annotations

from html import escape
from typing import Dict
from uuid import uuid4
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator

app = FastAPI(title="Perfil Público")

_profiles: Dict[str, "Profile"] = {}


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    bio: str = Field(min_length=1, max_length=2000)
    site: HttpUrl

    @field_validator("nome", "bio")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v

    @field_validator("site")
    @classmethod
    def validate_site_scheme(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("invalid URL scheme")
        return v


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nome: str
    bio: str
    site: str


@app.post("/perfil", status_code=status.HTTP_201_CREATED)
def create_profile(payload: ProfileCreate):
    profile_id = uuid4().hex
    profile = Profile(id=profile_id, nome=payload.nome, bio=payload.bio, site=str(payload.site))
    _profiles[profile_id] = profile
    return {"id": profile_id}


@app.get("/perfil/{id}", response_class=Response)
def get_profile(id: str):
    profile = _profiles.get(id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    safe_name = escape(profile.nome, quote=False)
    safe_bio = escape(profile.bio, quote=False)
    safe_site_text = escape(profile.site, quote=True)

    html = (
        "<!doctype html>"
        "<html lang='pt-BR'>"
        "<head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Perfil Público</title>"
        "</head>"
        "<body>"
        f"<h1>{safe_name}</h1>"
        f"<p>{safe_bio}</p>"
        f"<p><a href='{safe_site_text}' rel='noopener noreferrer nofollow' target='_blank'>Site pessoal</a></p>"
        "</body>"
        "</html>"
    )
    return Response(content=html, media_type="text/html; charset=utf-8")