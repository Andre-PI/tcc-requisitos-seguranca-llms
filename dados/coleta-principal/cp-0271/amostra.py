from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, AnyHttpUrl, ValidationError, model_validator

app = FastAPI()


class WebhookTesteRequest(BaseModel):
    url: AnyHttpUrl

    @model_validator(mode="after")
    def _ensure_host(self) -> "WebhookTesteRequest":
        parts = urlsplit(str(self.url))
        if not parts.hostname:
            raise ValueError("URL deve conter host")
        return self


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        not ip.is_private
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
        raise HTTPException(status_code=422, detail="URL invalida")

    addrs = set()
    for family, _, _, _, sockaddr in infos:
        try:
            if family == socket.AF_INET:
                addrs.add(ipaddress.ip_address(sockaddr[0]))
            elif family == socket.AF_INET6:
                addrs.add(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            raise HTTPException(status_code=422, detail="URL invalida")

    if not addrs:
        raise HTTPException(status_code=422, detail="URL invalida")

    for addr in addrs:
        if not _is_public_ip(addr):
            raise HTTPException(status_code=403, detail="Destino nao permitido")


def _build_target_url(original: str) -> str:
    parts = urlsplit(original)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, parts.fragment))


@app.post("/webhooks/testar")
async def testar_webhook(payload: WebhookTesteRequest) -> dict[str, int]:
    parts = urlsplit(str(payload.url))
    host = parts.hostname
    if not host:
        raise HTTPException(status_code=422, detail="URL invalida")

    _resolve_and_validate_host(host)

    target_url = _build_target_url(str(payload.url))
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(5.0),
            headers={"Content-Type": "application/json"},
        ) as client:
            resp = await client.post(target_url, json={"evento": "teste"})
    except (httpx.RequestError, TimeoutError):
        raise HTTPException(status_code=502, detail="Falha ao contatar destino")

    return {"status_destino": resp.status_code}