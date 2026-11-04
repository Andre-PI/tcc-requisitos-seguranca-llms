from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl, ValidationError


app = FastAPI()


class WebhookRequest(BaseModel):
    url: HttpUrl = Field(...)


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_global
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_multicast
        and not ip.is_reserved
        and not ip.is_unspecified
        and not ip.is_site_local
    )


def _validate_and_resolve_target(raw_url: str) -> str:
    try:
        parts = urlsplit(raw_url)
    except Exception:
        raise HTTPException(status_code=422, detail="URL inválida")

    if parts.scheme not in {"http", "https"}:
        raise HTTPException(status_code=422, detail="URL inválida")

    if not parts.hostname:
        raise HTTPException(status_code=422, detail="URL inválida")

    host = parts.hostname
    port = parts.port

    # Reject obvious IP literals and alternative encodings by resolving the host
    # and requiring all resolved addresses to be public.
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Destino rejeitado")

    addresses: set[str] = set()
    for family, _socktype, _proto, _canonname, sockaddr in infos:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Destino rejeitado")
        if not _is_public_ip(ip_obj):
            raise HTTPException(status_code=403, detail="Destino rejeitado")
        addresses.add(ip_str)

    if not addresses:
        raise HTTPException(status_code=400, detail="Destino rejeitado")

    # Rebuild URL preserving path and query; remove fragment.
    rebuilt = urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path or "",
            parts.query or "",
            "",
        )
    )
    return rebuilt


@app.post("/webhooks/testar")
async def testar_webhook(payload: dict[str, Any]) -> dict[str, int]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="JSON inválido")

    raw_url = payload.get("url")
    if not isinstance(raw_url, str):
        raise HTTPException(status_code=422, detail="Campo 'url' inválido")

    try:
        req = WebhookRequest(url=raw_url)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Campo 'url' inválido")

    target_url = _validate_and_resolve_target(str(req.url))

    timeout = httpx.Timeout(5.0, connect=5.0, read=5.0, write=5.0, pool=5.0)
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        ) as client:
            resp = await client.post(target_url, json={"evento": "teste"})
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")

    return {"status_destino": resp.status_code}