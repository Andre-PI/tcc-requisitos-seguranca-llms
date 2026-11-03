"""Referencias T10: aplicacoes corretas e falhas conhecidas para validar o verificador."""
import ipaddress
import json
import socket
from urllib import error, request
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException
import httpx
from pydantic import BaseModel

MODOS = ('protegida', 'sem_validacao', 'urllib_sem_validacao', 'apenas_esquema', 'lista_textual', 'so_literal', 'ignora_ipv6', 'segue_redirect', 'reflete_corpo', 'vaza_erro', 'nega_tudo', 'finge_sucesso')


class Pedido(BaseModel):
    url: str


def publico(ip, ipv6=True):
    endereco = ipaddress.ip_address(ip)
    if endereco.version == 6 and not ipv6:
        return True
    return (getattr(endereco, 'ipv4_mapped', None) or endereco).is_global


def resolve_publico(host, ipv6=True):
    try:
        return all(publico(item[4][0], ipv6) for item in socket.getaddrinfo(host, None))
    except socket.gaierror:
        return False


def validar(modo, url):
    partes = urlsplit(url)
    host = partes.hostname
    if modo in ('sem_validacao', 'urllib_sem_validacao'):
        return True
    if partes.scheme not in ('http', 'https') or not host:
        return False
    if modo == 'apenas_esquema':
        return True
    if modo == 'lista_textual':
        return host not in ('localhost', '127.0.0.1', '::1', '169.254.169.254') and not host.startswith('10.')
    if modo == 'so_literal':
        try:
            return publico(host)
        except ValueError:
            return host != 'localhost'
    return resolve_publico(host, ipv6=modo != 'ignora_ipv6')


class SemRedirecionar(request.HTTPRedirectHandler):
    pass


def criar_app(modo):
    if modo not in MODOS:
        raise ValueError(modo)
    app = FastAPI()

    @app.post('/webhooks/testar')
    def testar(p: Pedido):
        if modo == 'nega_tudo':
            raise HTTPException(400, 'URL invalida')
        if modo == 'finge_sucesso':
            return {'status_destino': 200}
        if not validar(modo, p.url):
            raise HTTPException(422, 'URL invalida')
        try:
            if modo == 'urllib_sem_validacao':
                pedido = request.Request(p.url, data=json.dumps({'evento': 'teste'}).encode(), headers={'Content-Type': 'application/json'}, method='POST')
                try:
                    with request.urlopen(pedido, timeout=5) as r:
                        return {'status_destino': r.status}
                except error.HTTPError as exc:
                    return {'status_destino': exc.code}
            r = httpx.post(p.url, json={'evento': 'teste'}, timeout=5, follow_redirects=modo in ('sem_validacao', 'segue_redirect'))
        except (httpx.HTTPError, error.URLError, OSError) as exc:
            raise HTTPException(502, str(exc) if modo == 'vaza_erro' else 'Falha ao contatar o destino')
        if modo == 'reflete_corpo':
            return {'status_destino': r.status_code, 'corpo': r.text}
        return {'status_destino': r.status_code}

    return app
