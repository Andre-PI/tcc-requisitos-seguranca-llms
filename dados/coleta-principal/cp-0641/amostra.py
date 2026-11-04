from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, AnyHttpUrl, Field


app = FastAPI()


class WebhookTesteRequest(BaseModel):
    url: AnyHttpUrl = Field(...)


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


def _resolve_and_validate_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="URL inválida")

    if not infos:
        raise HTTPException(status_code=403, detail="Destino rejeitado")

    seen = set()
    has_public = False

    for family, _, _, _, sockaddr in infos:
        ip_text = sockaddr[0]
        if ip_text in seen:
            continue
        seen.add(ip_text)
        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError:
            raise HTTPException(status_code=403, detail="Destino rejeitado")

        if not _is_public_ip(ip):
            raise HTTPException(status_code=403, detail="Destino rejeitado")
        has_public = True

    if not has_public:
        raise HTTPException(status_code=403, detail="Destino rejeitado")


def _build_target_url(original: AnyHttpUrl) -> str:
    parts = urlsplit(str(original))
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "", parts.query, ""))


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest) -> dict[str, int]:
    url = str(payload.url)
    parts = urlsplit(url)

    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise HTTPException(status_code=422, detail="URL inválida")

    _resolve_and_validate_host(parts.hostname)
    target_url = _build_target_url(payload.url)

    timeout = httpx.Timeout(5.0, connect=5.0, read=5.0, write=5.0, pool=5.0)
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=timeout,
            trust_env=False,
        ) as client:
            resp = await client.post(target_url, json={"evento": "teste"})
    except (httpx.RequestError, socket.timeout, TimeoutError):
        raise HTTPException(status_code=502, detail="Falha ao contatar o destino")

    return {"status_destino": resp.status_code}