from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, AnyHttpUrl, ValidationError


app = FastAPI()


class WebhookRequest(BaseModel):
    url: AnyHttpUrl


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return False
    if ip.version == 4:
        if ip.is_reserved or ip.is_global is False:
            return False
        # Block IPv4 special-use ranges that may not be covered consistently
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return False
        if ip in ipaddress.ip_network("192.0.0.0/24"):
            return False
        if ip in ipaddress.ip_network("198.18.0.0/15"):
            return False
        if ip in ipaddress.ip_network("240.0.0.0/4"):
            return False
    else:
        if ip.is_reserved or ip.is_global is False:
            return False
        # IPv6 special-use / metadata / documentation / unique-local
        blocked_v6 = [
            "fc00::/7",
            "fe80::/10",
            "::/128",
            "::1/128",
            "2001:db8::/32",
            "2001:10::/28",
            "64:ff9b:1::/48",
            "2002::/16",
        ]
        for cidr in blocked_v6:
            if ip in ipaddress.ip_network(cidr):
                return False
    return True


def _validate_and_resolve_url(raw_url: str) -> str:
    try:
        parsed = urlsplit(raw_url)
    except Exception:
        raise HTTPException(status_code=422, detail="URL inválida")

    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="URL rejeitada")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL rejeitada")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="URL rejeitada")

    host = parsed.hostname

    # Reject obvious literal IPs and alternative textual forms by parsing first.
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        if not _is_public_ip(literal_ip):
            raise HTTPException(status_code=403, detail="URL rejeitada")
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment))

    try:
        infos = socket.getaddrinfo(host, parsed.port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="URL rejeitada")

    resolved_any = False
    for family, _, _, _, sockaddr in infos:
        resolved_any = True
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(status_code=403, detail="URL rejeitada")
        if not _is_public_ip(ip_obj):
            raise HTTPException(status_code=403, detail="URL rejeitada")

    if not resolved_any:
        raise HTTPException(status_code=400, detail="URL rejeitada")

    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment))


@app.post("/webhooks/testar")
def testar_webhook(payload: dict):
    try:
        data = WebhookRequest.model_validate(payload)
    except ValidationError:
        raise HTTPException(status_code=422, detail="JSON inválido")

    target_url = _validate_and_resolve_url(str(data.url))

    try:
        with httpx.Client(
            follow_redirects=False,
            timeout=httpx.Timeout(5.0),
        ) as client:
            response = client.post(target_url, json={"evento": "teste"})
    except (httpx.RequestError, socket.timeout, TimeoutError):
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")

    return {"status_destino": response.status_code}