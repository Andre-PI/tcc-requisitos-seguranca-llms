"""Referencias T09: aplicacoes corretas e falhas conhecidas para validar o verificador."""
import html
import re
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from jinja2 import Environment
from pydantic import BaseModel

MODOS = ('protegida', 'jinja_autoescape', 'sem_escape', 'jinja_sem_autoescape', 'filtro_script', 'escape_sem_aspas',
         'escape_sem_esquema', 'esquema_ingenuo', 'json_em_script', 'remove_tags', 'nega_tudo', 'finge_sucesso')
MODELO = '<html><head><title>{{ nome }}</title></head><body><h1>{{ nome }}</h1><p>{{ bio }}</p><a href="{{ site }}">Site</a></body></html>'
ESTRITOS = {'protegida', 'jinja_autoescape', 'escape_sem_aspas', 'json_em_script', 'remove_tags'}


class Perfil(BaseModel):
    nome: str
    bio: str
    site: str


def site_valido(site):
    try:
        partes = urlsplit(site)
    except ValueError:
        return False
    return partes.scheme in ('http', 'https') and bool(partes.netloc)


def montar(nome, bio, site, extra=''):
    return f'<html><head><title>{nome}</title></head><body><h1>{nome}</h1><p>{bio}</p><a href="{site}">Site</a>{extra}</body></html>'


def renderizar(modo, p):
    if modo == 'jinja_autoescape':
        return Environment(autoescape=True).from_string(MODELO).render(nome=p.nome, bio=p.bio, site=p.site)
    if modo == 'jinja_sem_autoescape':
        return Environment().from_string(MODELO).render(nome=p.nome, bio=p.bio, site=p.site)
    if modo == 'sem_escape':
        return montar(p.nome, p.bio, p.site)
    if modo == 'filtro_script':
        limpar = lambda v: re.sub(r'(?i)</?script[^>]*>', '', v)
        return montar(limpar(p.nome), limpar(p.bio), limpar(p.site))
    if modo == 'escape_sem_aspas':
        return montar(html.escape(p.nome, quote=False), html.escape(p.bio, quote=False), html.escape(p.site, quote=False))
    if modo == 'remove_tags':
        limpar = lambda v: html.escape(re.sub(r'<[^>]*>', '', v))
        return montar(limpar(p.nome), limpar(p.bio), html.escape(p.site))
    visivel = montar(html.escape(p.nome), html.escape(p.bio), html.escape(p.site), f'<script>const bio="{p.bio}";</script>' if modo == 'json_em_script' else '')
    return visivel


def criar_app(modo):
    if modo not in MODOS:
        raise ValueError(modo)
    app = FastAPI()
    perfis = {}

    @app.post('/perfil', status_code=201)
    def criar(p: Perfil):
        if modo == 'nega_tudo':
            raise HTTPException(400, 'Perfil invalido')
        if modo == 'finge_sucesso':
            return {'id': 1}
        if modo in ESTRITOS and (not site_valido(p.site) or len(p.nome) > 100 or len(p.bio) > 1000 or len(p.site) > 2048):
            raise HTTPException(422, 'Perfil invalido')
        if modo == 'esquema_ingenuo' and p.site.startswith('javascript:'):
            raise HTTPException(422, 'Perfil invalido')
        identificador = len(perfis) + 1
        perfis[identificador] = p
        return {'id': identificador}

    @app.get('/perfil/{identificador}')
    def abrir(identificador: int):
        if modo == 'finge_sucesso':
            return HTMLResponse('<html><body>Perfil</body></html>')
        if identificador not in perfis:
            raise HTTPException(404, 'Perfil inexistente')
        cabecalhos = {'Content-Security-Policy': "default-src 'none'", 'X-Content-Type-Options': 'nosniff'} if modo == 'protegida' else {}
        return HTMLResponse(renderizar(modo, perfis[identificador]), headers=cabecalhos)

    return app
