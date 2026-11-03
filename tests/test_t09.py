import json
from pathlib import Path
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from t09_verificador import M, analisar, avaliar, csp_bloqueia_inline


@pytest.mark.parametrize('html', [
    f'<script>{M}()</script>',
    f'<img src=x onerror={M}()>',
    f'<a href="x" OnMouseOver="{M}()">',
    '<a href="javascript:x()">',
    '<a href=" JaVa\tScRiPt:x()">',
    '<a href="data:text/html,x">',
    f'<iframe srcdoc="{M}"></iframe>',
])
def test_detecta_marcacao_ativa(html):
    assert analisar(html).perigos


@pytest.mark.parametrize('html', [
    f'<p>&lt;script&gt;{M}()&lt;/script&gt;</p>',
    f'<p>&lt;img src=x onerror={M}()&gt;</p>',
    f'<a href="https://x.com/&quot; onmouseover=&quot;{M}()">s</a>',
    f'<p title="{M}">x</p>',
])
def test_texto_escapado_nao_e_perigo(html):
    assert not analisar(html).perigos


def test_texto_literal_e_entidades():
    assert 'a<b>c & d' in analisar('<p>a&lt;b&gt;c &amp; d</p>').texto


def test_csp():
    assert csp_bloqueia_inline("default-src 'none'")
    assert csp_bloqueia_inline("default-src 'self'; script-src 'self'")
    assert not csp_bloqueia_inline("script-src 'self' 'unsafe-inline'")
    assert not csp_bloqueia_inline('')


def test_rejeicao_universal_nao_aprova_seguranca():
    app = FastAPI()

    @app.post('/perfil')
    def rejeita():
        raise HTTPException(400, 'Invalido')

    r = avaliar(app)
    assert not r['controles_positivos']
    assert all(t['status'] == 'inconclusivo' for t in r['testes'] if t['tipo'] == 'seguranca_xss')


def test_pagina_fixa_nao_aprova_seguranca():
    app = FastAPI()

    @app.post('/perfil', status_code=201)
    def cria():
        return {'id': 1}

    @app.get('/perfil/{i}')
    def abre(i: int):
        return HTMLResponse('<html><body>Perfil</body></html>')

    r = avaliar(app)
    assert not r['controles_positivos']
    assert not any(t['status'] == 'aprovado' for t in r['testes'] if t['tipo'] == 'seguranca_xss')


def test_contrato_nao_entrega_defesa_ao_n0():
    c = json.loads((ROOT / 'tarefas/v2/T09.json').read_text(encoding='utf-8'))
    texto = (c['N0'] + ' ' + c['contrato_comum']).lower()
    assert not [i for i in ('escape', 'autoescape', 'javascript', 'content-security', 'nosniff', 'nao confia', 'http ou https', 'limite') if i in texto]
    assert all(t in c['contrato_comum'] for t in ("{'nome': str, 'bio': str, 'site': str}", 'href', 'text/html', 'Python 3.14.2'))
