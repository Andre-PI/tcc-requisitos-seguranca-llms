import ipaddress
import socket
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class WebhookPayload(BaseModel):
    url: HttpUrl


def is_safe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return False

    # Check for IPv4 mapped/compatible IPv6 addresses
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            return is_safe_ip(ip.ipv4_mapped)
        # Unique local IPv6 addresses
        if ip.is_site_local:
            return False

    # Check for AWS/cloud metadata address
    if ip == ipaddress.ip_address("169.254.169.254"):
        return False

    # Check for carrier-grade NAT (100.64.0.0/10)
    if isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10"):
        return False

    return ip.is_global


def validate_target_url(target_url: str) -> None:
    parsed = urlsplit(target_url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esquema de URL inválido. Apenas HTTP e HTTPS são permitidos.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host não informado ou inválido.",
        )

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível resolver o host informado.",
        )

    if not addr_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum endereço encontrado para o host informado.",
        )

    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Endereço de destino inválido.",
            )

        if not is_safe_ip(ip_obj):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Destino não permitido.",
            )


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookPayload):
    url_str = str(payload.url)
    validate_target_url(url_str)

    timeout = httpx.Timeout(5.0)

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
            resp = await client.post(url_str, json={"evento": "teste"})
            return {"status_destino": resp.status_code}
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao contatar o destino.",
        )