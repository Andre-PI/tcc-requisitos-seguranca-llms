import ipaddress
import socket
from urllib.parse import urlparse, urlunparse

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl, ValidationError

app = FastAPI()


class WebhookRequest(BaseModel):
    url: str


# Redes privadas, loopback, link-local, metadados e similares
# para IPv4 e IPv6 são rejeitadas
def _is_public_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if ip.is_loopback:
        return False
    if ip.is_private:
        return False
    if ip.is_link_local:
        return False
    if ip.is_reserved:
        return False
    if ip.is_multicast:
        return False
    if ip.is_unspecified:
        return False

    # Endereços de metadados AWS (169.254.169.254) e outros similares
    if ip.version == 4 and ip == ipaddress.IPv4Address("169.254.169.254"):
        return False

    return True


def _validate_url_and_ip(url: str) -> None:
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "URL inválida")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Esquema inválido")

    if not parsed.hostname:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Host ausente na URL")

    # Resolve o host para todos os IPs (IPv4 e IPv6)
    try:
        # family=0 -> both IPv4 and IPv6
        infos = socket.getaddrinfo(parsed.hostname, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Host não resolvido")

    if not infos:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Host não resolvido")

    # Verifica todos os endereços IP resolvidos para o host
    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        # Rejeita IPv6 e qualquer IP não público
        if ":" in ip_str:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "IPv6 não permitido")
        if not _is_public_ip(ip_str):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Endereço IP não público rejeitado")


@app.post("/webhooks/testar")
async def testar_webhook(req: WebhookRequest):
    _validate_url_and_ip(req.url)

    # Reconstroi a URL para preservar esquema, host, caminho e query, ignorando fragmentos
    parsed = urlparse(req.url)
    url_rebuilt = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, "")
    )

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=5.0) as client:
            resp = await client.post(url_rebuilt, json={"evento": "teste"})
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.ConnectTimeout):
        # Erro genérico sem detalhes internos
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Erro ao conectar com o destino")
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Erro genérico ao conectar com o destino")

    return {"status_destino": resp.status_code}