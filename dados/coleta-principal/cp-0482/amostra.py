from __future__ import annotations

import asyncio
import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, AnyHttpUrl, ValidationError


app = FastAPI()


class WebhookTesteRequest(BaseModel):
    url: AnyHttpUrl


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return False
    if ip.is_reserved or ip.is_site_local:
        return False
    return True


def _validate_url_and_resolve(url_str: str) -> tuple[str, str, int, str]:
    try:
        parsed = urlsplit(url_str)
    except Exception:
        raise HTTPException(status_code=422, detail="URL inválida")

    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=422, detail="URL inválida")
    if not parsed.hostname:
        raise HTTPException(status_code=422, detail="URL inválida")
    if parsed.username is not None or parsed.password is not None:
        raise HTTPException(status_code=422, detail="URL inválida")

    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Destino inválido")

    addrs: set[ipaddress._BaseAddress] = set()
    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Destino inválido")
        addrs.add(ip)

    if not addrs:
        raise HTTPException(status_code=400, detail="Destino inválido")

    for ip in addrs:
        if not _is_public_ip(ip):
            raise HTTPException(status_code=403, detail="Destino não permitido")

    return parsed.scheme, host, port, urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment))


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest) -> dict[str, Any]:
    scheme, host, port, target_url = _validate_url_and_resolve(str(payload.url))

    timeout = httpx.Timeout(5.0, connect=5.0, read=5.0, write=5.0, pool=5.0)
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.post(target_url, json={"evento": "teste"})
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout, httpx.RemoteProtocolError, httpx.LocalProtocolError):
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")

    return {"status_destino": response.status_code}