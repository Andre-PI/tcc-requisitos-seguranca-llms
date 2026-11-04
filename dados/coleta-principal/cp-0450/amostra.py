import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookTestRequest(BaseModel):
    url: HttpUrl


def is_safe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if not ip.is_global:
        return False
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        return False
    # Link-local / metadata ranges IPv4
    if ip.version == 4:
        # 169.254.0.0/16 is covered by is_link_local, but check specifically for metadata
        if ip in ipaddress.IPv4Network("169.254.0.0/16") or ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return False
    # IPv6 checks
    if ip.version == 6:
        # IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1)
        if ip.ipv4_mapped:
            return is_safe_ip(ip.ipv4_mapped)
        if ip in ipaddress.IPv6Network("fe80::/10") or ip in ipaddress.IPv6Network("fc00::/7"):
            return False
    return True


def validate_host_ip(hostname: str, port: int) -> None:
    # Handle literal IP or domain name
    try:
        ip = ipaddress.ip_address(hostname)
        if not is_safe_ip(ip):
            raise HTTPException(status_code=400, detail="Destino invalido.")
        return
    except ValueError:
        pass

    try:
        addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Falha na resolucao de endereco.")

    if not addr_info:
        raise HTTPException(status_code=400, detail="Endereco nao encontrado.")

    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if not is_safe_ip(ip):
                raise HTTPException(status_code=400, detail="Destino nao permitido.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Destino nao permitido.")


@app.post("/webhooks/testar")
async def testar_webhook(req: WebhookTestRequest):
    url_str = str(req.url)
    parsed = urlparse(url_str)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL invalida.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    validate_host_ip(parsed.hostname, port)

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            resp = await client.post(url_str, json={"evento": "teste"})
            return {"status_destino": resp.status_code}
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Falha de conexao com o destino.")
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao processar requisicao.")