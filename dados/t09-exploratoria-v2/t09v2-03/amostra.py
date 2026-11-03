from fastapi import FastAPI, Request, Response, status, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator, ValidationError
from typing import Dict
from uuid import uuid4
from urllib.parse import urlparse
from jinja2 import Environment, select_autoescape

app = FastAPI()

# In-memory storage for profiles
_profiles: Dict[str, Dict[str, str]] = {}

# Jinja2 environment with autoescape enabled for html and xml
jinja_env = Environment(
    autoescape=select_autoescape(["html", "xml"]),
)

# Template for profile page
_profile_template = jinja_env.from_string(
    """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta http-equiv="X-Content-Type-Options" content="nosniff"/>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; img-src 'self'; connect-src 'none'; frame-src 'none'; script-src 'none';"/>
<title>Perfil de {{ nome }}</title>
</head>
<body>
<h1>{{ nome }}</h1>
<p>{{ bio }}</p>
<p><a href="{{ site }}" rel="noopener noreferrer" target="_blank">Site pessoal</a></p>
</body>
</html>
"""
)

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc:
            return False
        # Reject javascript:, data: and variants
        if parsed.scheme.lower() in ("javascript", "data", "vbscript"):
            return False
        # Any other validation not required by spec
        return True
    except Exception:
        return False

class PerfilIn(BaseModel):
    nome: str = Field(..., max_length=100)
    bio: str = Field(..., max_length=1000)
    site: str = Field(..., max_length=2048)

    @validator("site")
    def check_site(cls, v: str) -> str:
        if not is_valid_url(v):
            raise ValueError("site must be an absolute http or https URL")
        return v

@app.post("/perfil", status_code=status.HTTP_201_CREATED)
async def criar_perfil(perfil: PerfilIn):
    perfil_id = str(uuid4())
    _profiles[perfil_id] = perfil.model_dump()
    return JSONResponse(status_code=201, content={"id": perfil_id})

@app.get("/perfil/{perfil_id}", response_class=HTMLResponse)
async def obter_perfil(perfil_id: str, response: Response):
    perfil = _profiles.get(perfil_id)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    # Render template with escaped content (autoescape enabled)
    html = _profile_template.render(
        nome=perfil["nome"],
        bio=perfil["bio"],
        site=perfil["site"],
    )
    response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'self'; img-src 'self'; connect-src 'none'; frame-src 'none'; script-src 'none';"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return html